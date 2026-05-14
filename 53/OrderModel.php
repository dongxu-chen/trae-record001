<?php

require_once __DIR__ . '/db.php';

class OrderModel
{
    private $pdo;

    private $allowedStatuses = ['pending', 'processing', 'completed', 'cancelled'];

    private $paymentTimeout = 300;

    public function __construct($pdo = null)
    {
        $this->pdo = $pdo ?? require __DIR__ . '/db.php';
        $this->initQueueTable();
    }

    private function initQueueTable()
    {
        $sql = "CREATE TABLE IF NOT EXISTS event_queue (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            order_id INT NOT NULL,
            payload TEXT,
            status ENUM('pending','processing','sent','failed') DEFAULT 'pending',
            retries INT DEFAULT 0,
            next_attempt_at DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME NULL,
            INDEX idx_status (status),
            INDEX idx_event_type (event_type),
            INDEX idx_order_id (order_id),
            INDEX idx_next_attempt (next_attempt_at)
        )";
        $this->pdo->exec($sql);
    }

    public function getAll()
    {
        $stmt = $this->pdo->query("SELECT * FROM orders ORDER BY created_at DESC");
        return $stmt->fetchAll();
    }

    public function getById($id)
    {
        $stmt = $this->pdo->prepare("SELECT * FROM orders WHERE id = :id");
        $stmt->execute([':id' => (int) $id]);
        return $stmt->fetch();
    }

    public function create($data)
    {
        $status = $this->sanitizeStatus($data['status'] ?? 'pending');
        
        $sql = "INSERT INTO orders (customer_name, customer_email, total_amount, status, version, created_at)
                VALUES (:customer_name, :customer_email, :total_amount, :status, 1, NOW())";
        
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([
            ':customer_name'  => $this->sanitizeString($data['customer_name'], 100),
            ':customer_email' => $this->sanitizeString($data['customer_email'], 255),
            ':total_amount'   => $this->sanitizeDecimal($data['total_amount']),
            ':status'         => $status,
        ]);

        $orderId = $this->pdo->lastInsertId();

        $this->enqueueEvent('order.created', $orderId, [
            'order_id' => $orderId,
            'total_amount' => $this->sanitizeDecimal($data['total_amount']),
            'customer_name' => $this->sanitizeString($data['customer_name'], 100),
            'customer_email' => $this->sanitizeString($data['customer_email'], 255),
            'created_at' => date('Y-m-d H:i:s')
        ]);

        return $this->getById($orderId);
    }

    public function update($id, $data, $expectedVersion = null)
    {
        $currentOrder = $this->getById($id);
        if (!$currentOrder) {
            throw new RuntimeException('Order not found');
        }

        $currentVersion = $currentOrder['version'] ?? 1;
        if ($expectedVersion !== null && (int) $expectedVersion !== (int) $currentVersion) {
            throw new RuntimeException('Optimistic lock conflict: order has been modified by another process');
        }

        $updates = [];
        $params = [':id' => (int) $id];
        $oldStatus = $currentOrder['status'];
        $newStatus = null;

        if (isset($data['customer_name'])) {
            $updates[] = 'customer_name = :customer_name';
            $params[':customer_name'] = $this->sanitizeString($data['customer_name'], 100);
        }

        if (isset($data['customer_email'])) {
            $updates[] = 'customer_email = :customer_email';
            $params[':customer_email'] = $this->sanitizeString($data['customer_email'], 255);
        }

        if (isset($data['total_amount'])) {
            $updates[] = 'total_amount = :total_amount';
            $params[':total_amount'] = $this->sanitizeDecimal($data['total_amount']);
        }

        if (isset($data['status'])) {
            $newStatus = $this->sanitizeStatus($data['status']);
            if ($newStatus === null) {
                throw new RuntimeException('Invalid status value');
            }
            $updates[] = 'status = :status';
            $params[':status'] = $newStatus;
        }

        if (empty($updates)) {
            return $currentOrder;
        }

        $updates[] = 'version = version + 1';
        $params[':expected_version'] = (int) $currentVersion;

        $sql = "UPDATE orders SET " . implode(', ', $updates) . " WHERE id = :id AND version = :expected_version";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute($params);

        if ($stmt->rowCount() === 0) {
            throw new RuntimeException('Optimistic lock conflict: order has been modified by another process');
        }

        if ($newStatus !== null && $newStatus !== $oldStatus) {
            $this->handleStatusChange($id, $oldStatus, $newStatus);
        }

        return $this->getById($id);
    }

    public function delete($id)
    {
        $order = $this->getById($id);
        if (!$order) {
            return false;
        }

        $this->enqueueEvent('order.deleted', $id, [
            'order_id' => $id,
            'deleted_at' => date('Y-m-d H:i:s')
        ]);

        $stmt = $this->pdo->prepare("DELETE FROM orders WHERE id = :id");
        return $stmt->execute([':id' => (int) $id]);
    }

    public function processTimeoutOrders()
    {
        $timeout = time() - $this->paymentTimeout;
        $timeoutDate = date('Y-m-d H:i:s', $timeout);

        $this->pdo->beginTransaction();

        try {
            $sql = "SELECT id FROM orders 
                    WHERE status = 'pending' 
                      AND created_at < :timeout_date
                    FOR UPDATE";

            $stmt = $this->pdo->prepare($sql);
            $stmt->execute([':timeout_date' => $timeoutDate]);
            $expiredOrders = $stmt->fetchAll(PDO::FETCH_COLUMN);

            $count = 0;
            foreach ($expiredOrders as $orderId) {
                $order = $this->getById($orderId);
                if ($order && $order['status'] === 'pending') {
                    $this->cancelOrderInternal($orderId, 'Payment timeout');
                    $count++;
                }
            }

            $this->pdo->commit();
            return $count;

        } catch (Exception $e) {
            $this->pdo->rollBack();
            throw $e;
        }
    }

    public function processQueue($batchSize = 10)
    {
        $this->pdo->beginTransaction();

        try {
            $sql = "SELECT * FROM event_queue 
                    WHERE status = 'pending'
                      AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                    ORDER BY id ASC
                    LIMIT :batch_size
                    FOR UPDATE SKIP LOCKED";

            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':batch_size', (int) $batchSize, PDO::PARAM_INT);
            $stmt->execute();
            $events = $stmt->fetchAll();

            $processed = 0;
            foreach ($events as $event) {
                $this->processEvent($event);
                $processed++;
            }

            $this->pdo->commit();
            return $processed;

        } catch (Exception $e) {
            $this->pdo->rollBack();
            throw $e;
        }
    }

    private function processEvent($event)
    {
        $eventId = (int) $event['id'];
        $payload = json_decode($event['payload'], true);
        $success = $this->dispatchEvent($event['event_type'], $payload);

        if ($success) {
            $sql = "UPDATE event_queue 
                    SET status = 'sent', 
                        processed_at = NOW() 
                    WHERE id = :id";
        } else {
            $retries = (int) $event['retries'] + 1;
            if ($retries >= 5) {
                $sql = "UPDATE event_queue SET status = 'failed' WHERE id = :id";
            } else {
                $nextAttempt = date('Y-m-d H:i:s', time() + (60 * $retries));
                $sql = "UPDATE event_queue 
                        SET status = 'pending',
                            retries = :retries,
                            next_attempt_at = :next_attempt
                        WHERE id = :id";
            }
        }

        $stmt = $this->pdo->prepare($sql);
        $stmt->bindValue(':id', $eventId);

        if (!$success && $retries < 5 && isset($nextAttempt)) {
            $stmt->bindValue(':retries', $retries);
            $stmt->bindValue(':next_attempt', $nextAttempt);
        }

        $stmt->execute();
    }

    private function dispatchEvent($eventType, $payload)
    {
        $webhookUrl = $this->getWebhookUrl();
        if (empty($webhookUrl)) {
            return true;
        }

        $ch = curl_init($webhookUrl);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
            'event' => $eventType,
            'payload' => $payload,
            'timestamp' => time()
        ]));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        return $httpCode === 200;
    }

    private function getWebhookUrl()
    {
        $stmt = $this->pdo->query("SELECT value FROM settings WHERE `key` = 'webhook_url' LIMIT 1");
        $row = $stmt->fetch();
        return $row ? $row['value'] : null;
    }

    private function enqueueEvent($eventType, $orderId, $payload)
    {
        $sql = "INSERT INTO event_queue (event_type, order_id, payload, status)
                VALUES (:event_type, :order_id, :payload, 'pending')";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([
            ':event_type' => $eventType,
            ':order_id' => (int) $orderId,
            ':payload' => json_encode($payload)
        ]);

        return $this->pdo->lastInsertId();
    }

    private function handleStatusChange($orderId, $oldStatus, $newStatus)
    {
        $eventMap = [
            'pending->processing' => 'order.confirmed',
            'pending->cancelled'  => 'order.cancelled',
            'processing->completed' => 'order.completed',
            'processing->cancelled' => 'order.cancelled',
            'pending->completed'  => 'order.completed',
        ];

        $transition = $oldStatus . '->' . $newStatus;
        if (isset($eventMap[$transition])) {
            $this->enqueueEvent($eventMap[$transition], $orderId, [
                'order_id' => $orderId,
                'old_status' => $oldStatus,
                'new_status' => $newStatus,
                'changed_at' => date('Y-m-d H:i:s')
            ]);
        }
    }

    private function cancelOrderInternal($orderId, $reason = '')
    {
        $order = $this->getById($orderId);
        if (!$order || $order['status'] !== 'pending') {
            return false;
        }

        $sql = "UPDATE orders SET status = 'cancelled', version = version + 1 WHERE id = :id";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([':id' => (int) $orderId]);

        if ($stmt->rowCount() > 0) {
            $this->enqueueEvent('order.timeout', $orderId, [
                'order_id' => $orderId,
                'reason' => $reason,
                'timeout_at' => date('Y-m-d H:i:s')
            ]);
            return true;
        }

        return false;
    }

    public function markAsPaid($orderId)
    {
        $order = $this->getById($orderId);
        if (!$order) {
            throw new RuntimeException('Order not found');
        }

        if ($order['status'] !== 'pending') {
            throw new RuntimeException('Order is not in pending status');
        }

        return $this->update($orderId, ['status' => 'processing'], $order['version']);
    }

    public function getTimeoutSeconds()
    {
        return $this->paymentTimeout;
    }

    public function getPendingEvents()
    {
        $stmt = $this->pdo->query("SELECT * FROM event_queue WHERE status = 'pending' ORDER BY id DESC");
        return $stmt->fetchAll();
    }

    private function sanitizeString($value, $maxLength)
    {
        if (!is_string($value)) {
            $value = (string) $value;
        }
        $value = trim($value);
        $value = strip_tags($value);
        $value = mb_substr($value, 0, $maxLength, 'UTF-8');
        return $value;
    }

    private function sanitizeDecimal($value)
    {
        return number_format((float) $value, 2, '.', '');
    }

    private function sanitizeStatus($status)
    {
        $status = strtolower(trim((string) $status));
        return in_array($status, $this->allowedStatuses, true) ? $status : null;
    }
}

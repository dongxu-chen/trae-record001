<?php

header('Content-Type: application/json');

require_once __DIR__ . '/db.php';

class WebhookReceiver
{
    private $pdo;
    private $receivedEvents = [];

    public function __construct($pdo = null)
    {
        $this->pdo = $pdo ?? require __DIR__ . '/db.php';
        $this->initWebhookTable();
    }

    private function initWebhookTable()
    {
        $sql = "CREATE TABLE IF NOT EXISTS webhook_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            order_id INT NULL,
            payload TEXT,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_event_type (event_type),
            INDEX idx_order_id (order_id)
        )";
        $this->pdo->exec($sql);

        $sql = "CREATE TABLE IF NOT EXISTS settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `key` VARCHAR(100) NOT NULL UNIQUE,
            value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )";
        $this->pdo->exec($sql);
    }

    public function handleRequest()
    {
        $method = $_SERVER['REQUEST_METHOD'];

        if ($method === 'OPTIONS') {
            $this->sendResponse([], 200);
            return;
        }

        if ($method === 'GET') {
            $this->handleGet();
            return;
        }

        if ($method === 'POST') {
            $this->handlePost();
            return;
        }

        $this->sendResponse(['error' => 'Method not allowed'], 405);
    }

    private function handleGet()
    {
        $action = $_GET['action'] ?? '';

        if ($action === 'list') {
            $this->listLogs();
            return;
        }

        if ($action === 'config') {
            $this->getConfig();
            return;
        }

        $this->sendResponse([
            'message' => 'Webhook Receiver',
            'endpoints' => [
                'GET  /webhook.php?action=list'   => 'List received webhook events',
                'GET  /webhook.php?action=config' => 'Get current webhook config',
                'POST /webhook.php?action=config' => 'Set webhook URL config',
                'POST /webhook.php'               => 'Receive webhook event'
            ]
        ]);
    }

    private function handlePost()
    {
        $action = $_GET['action'] ?? '';

        if ($action === 'config') {
            $this->setConfig();
            return;
        }

        $this->receiveEvent();
    }

    private function receiveEvent()
    {
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);

        if (!$data) {
            $this->sendResponse(['error' => 'Invalid JSON payload'], 400);
            return;
        }

        $eventType = $data['event'] ?? 'unknown';
        $payload = $data['payload'] ?? [];
        $orderId = isset($payload['order_id']) ? (int) $payload['order_id'] : null;

        $sql = "INSERT INTO webhook_logs (event_type, order_id, payload)
                VALUES (:event_type, :order_id, :payload)";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([
            ':event_type' => $this->sanitizeString($eventType, 50),
            ':order_id' => $orderId,
            ':payload' => json_encode($data)
        ]);

        $this->dispatchEvent($eventType, $payload);

        $this->sendResponse([
            'success' => true,
            'message' => 'Webhook received',
            'event_type' => $eventType,
            'order_id' => $orderId
        ]);
    }

    private function dispatchEvent($eventType, $payload)
    {
        $handlers = [
            'order.created'   => 'onOrderCreated',
            'order.confirmed' => 'onOrderConfirmed',
            'order.completed' => 'onOrderCompleted',
            'order.cancelled' => 'onOrderCancelled',
            'order.timeout'   => 'onOrderTimeout',
            'order.deleted'   => 'onOrderDeleted'
        ];

        if (isset($handlers[$eventType]) && method_exists($this, $handlers[$eventType])) {
            $this->{$handlers[$eventType]}($payload);
        }

        $this->receivedEvents[] = [
            'type' => $eventType,
            'payload' => $payload,
            'time' => date('Y-m-d H:i:s')
        ];
    }

    private function onOrderCreated($payload)
    {
        error_log('[Webhook] Order created: ' . json_encode($payload));
    }

    private function onOrderConfirmed($payload)
    {
        error_log('[Webhook] Order confirmed: ' . json_encode($payload));
    }

    private function onOrderCompleted($payload)
    {
        error_log('[Webhook] Order completed: ' . json_encode($payload));
    }

    private function onOrderCancelled($payload)
    {
        error_log('[Webhook] Order cancelled: ' . json_encode($payload));
    }

    private function onOrderTimeout($payload)
    {
        error_log('[Webhook] Order timeout: ' . json_encode($payload));
    }

    private function onOrderDeleted($payload)
    {
        error_log('[Webhook] Order deleted: ' . json_encode($payload));
    }

    private function listLogs()
    {
        $limit = isset($_GET['limit']) ? (int) $_GET['limit'] : 50;
        $limit = min($limit, 100);

        $stmt = $this->pdo->prepare("SELECT * FROM webhook_logs ORDER BY id DESC LIMIT :limit");
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        $logs = $stmt->fetchAll();

        foreach ($logs as &$log) {
            $log['payload'] = json_decode($log['payload'], true);
        }

        $this->sendResponse(['logs' => $logs]);
    }

    private function getConfig()
    {
        $stmt = $this->pdo->query("SELECT `key`, value FROM settings");
        $config = [];
        while ($row = $stmt->fetch()) {
            $config[$row['key']] = $row['value'];
        }

        $this->sendResponse(['config' => $config]);
    }

    private function setConfig()
    {
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);

        if (!$data) {
            $this->sendResponse(['error' => 'Invalid JSON payload'], 400);
            return;
        }

        if (isset($data['webhook_url'])) {
            $url = $this->sanitizeString($data['webhook_url'], 500);

            if (!filter_var($url, FILTER_VALIDATE_URL)) {
                $this->sendResponse(['error' => 'Invalid URL'], 400);
                return;
            }

            $sql = "INSERT INTO settings (`key`, value)
                    VALUES ('webhook_url', :value)
                    ON DUPLICATE KEY UPDATE value = :value";

            $stmt = $this->pdo->prepare($sql);
            $stmt->execute([':value' => $url]);

            $this->sendResponse([
                'success' => true,
                'message' => 'Webhook URL updated',
                'webhook_url' => $url
            ]);
            return;
        }

        $this->sendResponse(['error' => 'Missing webhook_url'], 400);
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

    private function sendResponse($data, $status = 200)
    {
        http_response_code($status);
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Headers: Content-Type');
        header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }
}

$receiver = new WebhookReceiver();
$receiver->handleRequest();

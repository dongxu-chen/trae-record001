<?php

class PaymentSimulator
{
    private $secret = 'payment_secret_key_123456';

    private $paymentRecords = [];

    private $pdo;

    public function __construct($pdo = null)
    {
        $this->pdo = $pdo ?? require __DIR__ . '/db.php';
        $this->initPaymentTable();
    }

    private function initPaymentTable()
    {
        $sql = "CREATE TABLE IF NOT EXISTS payment_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            payment_no VARCHAR(64) NOT NULL UNIQUE,
            amount DECIMAL(10,2) NOT NULL,
            status ENUM('pending','paid','failed','cancelled') DEFAULT 'pending',
            payment_method VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            paid_at DATETIME NULL,
            INDEX idx_order_id (order_id),
            INDEX idx_status (status)
        )";
        $this->pdo->exec($sql);
    }

    public function createPayment($orderId, $amount, $paymentMethod = 'alipay')
    {
        $paymentNo = 'PAY' . date('YmdHis') . str_pad(rand(0, 9999), 4, '0', STR_PAD_LEFT);

        $sql = "INSERT INTO payment_records (order_id, payment_no, amount, status, payment_method)
                VALUES (:order_id, :payment_no, :amount, 'pending', :payment_method)";

        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([
            ':order_id' => (int) $orderId,
            ':payment_no' => $paymentNo,
            ':amount' => number_format((float) $amount, 2, '.', ''),
            ':payment_method' => $this->sanitizeString($paymentMethod, 50)
        ]);

        $paymentId = $this->pdo->lastInsertId();

        return [
            'id' => (int) $paymentId,
            'payment_no' => $paymentNo,
            'order_id' => (int) $orderId,
            'amount' => number_format((float) $amount, 2, '.', ''),
            'status' => 'pending',
            'payment_method' => $paymentMethod,
            'payment_url' => '/mock/pay/' . $paymentNo,
            'expire_seconds' => 300
        ];
    }

    public function simulatePay($paymentNo, $success = true)
    {
        $payment = $this->getPaymentByNo($paymentNo);
        if (!$payment) {
            return false;
        }

        if ($payment['status'] !== 'pending') {
            return false;
        }

        $newStatus = $success ? 'paid' : 'failed';

        $sql = "UPDATE payment_records SET status = :status, paid_at = :paid_at WHERE payment_no = :payment_no";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([
            ':status' => $newStatus,
            ':paid_at' => $success ? date('Y-m-d H:i:s') : null,
            ':payment_no' => $paymentNo
        ]);

        return [
            'payment_no' => $paymentNo,
            'order_id' => (int) $payment['order_id'],
            'amount' => $payment['amount'],
            'status' => $newStatus,
            'success' => $success,
            'callback_data' => $this->generateCallbackData($paymentNo, $success)
        ];
    }

    public function getPaymentByNo($paymentNo)
    {
        $stmt = $this->pdo->prepare("SELECT * FROM payment_records WHERE payment_no = :payment_no");
        $stmt->execute([':payment_no' => $paymentNo]);
        return $stmt->fetch();
    }

    public function getPaymentByOrderId($orderId)
    {
        $stmt = $this->pdo->prepare("SELECT * FROM payment_records WHERE order_id = :order_id ORDER BY created_at DESC LIMIT 1");
        $stmt->execute([':order_id' => (int) $orderId]);
        return $stmt->fetch();
    }

    private function generateCallbackData($paymentNo, $success)
    {
        $payment = $this->getPaymentByNo($paymentNo);
        if (!$payment) {
            return null;
        }

        $data = [
            'order_id' => (int) $payment['order_id'],
            'payment_no' => $paymentNo,
            'amount' => $payment['amount'],
            'status' => $success ? 'paid' : 'failed',
            'timestamp' => time(),
            'nonce' => bin2hex(random_bytes(16))
        ];

        $data['sign'] = $this->generateSign($data);

        return $data;
    }

    public function verifyCallback($data)
    {
        if (!isset($data['sign'])) {
            return false;
        }

        $receivedSign = $data['sign'];
        unset($data['sign']);

        $calculatedSign = $this->generateSign($data);

        return hash_equals($calculatedSign, $receivedSign);
    }

    private function generateSign($data)
    {
        ksort($data);
        $string = http_build_query($data) . '&secret=' . $this->secret;
        return hash_hmac('sha256', $string, $this->secret);
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

    public function cancelPayment($paymentNo)
    {
        $payment = $this->getPaymentByNo($paymentNo);
        if (!$payment || $payment['status'] !== 'pending') {
            return false;
        }

        $sql = "UPDATE payment_records SET status = 'cancelled' WHERE payment_no = :payment_no";
        $stmt = $this->pdo->prepare($sql);
        $stmt->execute([':payment_no' => $paymentNo]);

        return true;
    }
}

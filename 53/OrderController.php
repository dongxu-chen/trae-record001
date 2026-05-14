<?php

require_once __DIR__ . '/OrderModel.php';
require_once __DIR__ . '/Validator.php';
require_once __DIR__ . '/PaymentSimulator.php';

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

class OrderController
{
    private $orderModel;
    private $paymentSimulator;

    private $allowedFields = [
        'customer_name',
        'customer_email',
        'total_amount',
        'status',
        'version',
        'payment_method'
    ];

    public function __construct($orderModel = null, $paymentSimulator = null)
    {
        $this->orderModel = $orderModel ?? new OrderModel();
        $this->paymentSimulator = $paymentSimulator ?? new PaymentSimulator();
    }

    public function getAll(Request $request, Response $response, $args)
    {
        $orders = $this->orderModel->getAll();
        return $this->jsonResponse($response, ['orders' => $orders]);
    }

    public function getById(Request $request, Response $response, $args)
    {
        $id = (int) $args['id'];
        $order = $this->orderModel->getById($id);

        if (!$order) {
            return $this->jsonResponse($response, ['error' => 'Order not found'], 404);
        }

        return $this->jsonResponse($response, ['order' => $order]);
    }

    public function create(Request $request, Response $response, $args)
    {
        $data = $this->filterWhitelist($request->getParsedBody());

        $errors = Validator::validate($data, [
            'customer_name'  => ['required', 'min:2', 'max:100'],
            'customer_email' => ['required', 'email', 'max:255'],
            'total_amount'   => ['required', 'numeric', 'positive'],
        ]);

        if (!empty($errors)) {
            return $this->jsonResponse($response, ['errors' => $errors], 400);
        }

        $data = $this->sanitizeData($data);

        try {
            $order = $this->orderModel->create($data);
            return $this->jsonResponse($response, ['order' => $order], 201);
        } catch (RuntimeException $e) {
            return $this->jsonResponse($response, ['error' => $e->getMessage()], 400);
        }
    }

    public function update(Request $request, Response $response, $args)
    {
        $id = (int) $args['id'];
        $existingOrder = $this->orderModel->getById($id);

        if (!$existingOrder) {
            return $this->jsonResponse($response, ['error' => 'Order not found'], 404);
        }

        $data = $this->filterWhitelist($request->getParsedBody());

        $rules = [];
        if (isset($data['customer_name'])) {
            $rules['customer_name'] = ['min:2', 'max:100'];
        }
        if (isset($data['customer_email'])) {
            $rules['customer_email'] = ['email', 'max:255'];
        }
        if (isset($data['total_amount'])) {
            $rules['total_amount'] = ['numeric', 'positive'];
        }

        if (!empty($rules)) {
            $errors = Validator::validate($data, $rules);
            if (!empty($errors)) {
                return $this->jsonResponse($response, ['errors' => $errors], 400);
            }
        }

        $data = $this->sanitizeData($data);
        $expectedVersion = isset($data['version']) ? (int) $data['version'] : null;
        unset($data['version']);

        try {
            $order = $this->orderModel->update($id, $data, $expectedVersion);
            return $this->jsonResponse($response, ['order' => $order]);
        } catch (RuntimeException $e) {
            $message = $e->getMessage();
            $status = strpos($message, 'Optimistic lock') !== false ? 409 : 400;
            return $this->jsonResponse($response, ['error' => $message], $status);
        }
    }

    public function delete(Request $request, Response $response, $args)
    {
        $id = (int) $args['id'];
        $deleted = $this->orderModel->delete($id);

        if (!$deleted) {
            return $this->jsonResponse($response, ['error' => 'Order not found'], 404);
        }

        return $this->jsonResponse($response, ['message' => 'Order deleted successfully']);
    }

    public function createPayment(Request $request, Response $response, $args)
    {
        $id = (int) $args['id'];
        $order = $this->orderModel->getById($id);

        if (!$order) {
            return $this->jsonResponse($response, ['error' => 'Order not found'], 404);
        }

        if ($order['status'] !== 'pending') {
            return $this->jsonResponse($response, ['error' => 'Order is not in pending status'], 400);
        }

        $data = $this->filterWhitelist($request->getParsedBody());
        $paymentMethod = $data['payment_method'] ?? 'alipay';

        $payment = $this->paymentSimulator->createPayment(
            $order['id'],
            $order['total_amount'],
            $paymentMethod
        );

        return $this->jsonResponse($response, [
            'payment' => $payment,
            'timeout_seconds' => $this->orderModel->getTimeoutSeconds()
        ], 201);
    }

    public function simulatePay(Request $request, Response $response, $args)
    {
        $paymentNo = $args['payment_no'];
        $data = $this->filterWhitelist($request->getParsedBody());
        $success = isset($data['success']) ? (bool) $data['success'] : true;

        $result = $this->paymentSimulator->simulatePay($paymentNo, $success);

        if (!$result) {
            return $this->jsonResponse($response, ['error' => 'Payment not found or already processed'], 400);
        }

        if ($result['success']) {
            try {
                $order = $this->orderModel->markAsPaid($result['order_id']);
                $result['order'] = $order;
            } catch (RuntimeException $e) {
                return $this->jsonResponse($response, ['error' => $e->getMessage()], 400);
            }
        }

        return $this->jsonResponse($response, $result);
    }

    public function paymentCallback(Request $request, Response $response, $args)
    {
        $data = $request->getParsedBody();

        if (!$this->paymentSimulator->verifyCallback($data)) {
            return $this->jsonResponse($response, ['error' => 'Invalid signature'], 400);
        }

        $orderId = (int) $data['order_id'];
        $status = $data['status'] ?? 'unknown';

        $order = $this->orderModel->getById($orderId);
        if (!$order) {
            return $this->jsonResponse($response, ['error' => 'Order not found'], 404);
        }

        if ($status === 'paid' && $order['status'] === 'pending') {
            try {
                $updatedOrder = $this->orderModel->markAsPaid($orderId);
                return $this->jsonResponse($response, [
                    'success' => true,
                    'message' => 'Payment processed successfully',
                    'order' => $updatedOrder
                ]);
            } catch (RuntimeException $e) {
                return $this->jsonResponse($response, ['error' => $e->getMessage()], 400);
            }
        }

        return $this->jsonResponse($response, [
            'success' => true,
            'message' => 'Callback received'
        ]);
    }

    public function processTimeout(Request $request, Response $response, $args)
    {
        try {
            $count = $this->orderModel->processTimeoutOrders();
            return $this->jsonResponse($response, [
                'success' => true,
                'cancelled_count' => $count,
                'message' => "Cancelled {$count} timeout orders"
            ]);
        } catch (Exception $e) {
            return $this->jsonResponse($response, ['error' => $e->getMessage()], 500);
        }
    }

    public function processQueue(Request $request, Response $response, $args)
    {
        try {
            $count = $this->orderModel->processQueue();
            return $this->jsonResponse($response, [
                'success' => true,
                'processed_count' => $count,
                'message' => "Processed {$count} queue items"
            ]);
        } catch (Exception $e) {
            return $this->jsonResponse($response, ['error' => $e->getMessage()], 500);
        }
    }

    public function getPaymentStatus(Request $request, Response $response, $args)
    {
        $id = (int) $args['id'];
        $payment = $this->paymentSimulator->getPaymentByOrderId($id);

        if (!$payment) {
            return $this->jsonResponse($response, ['error' => 'Payment record not found'], 404);
        }

        return $this->jsonResponse($response, ['payment' => $payment]);
    }

    private function filterWhitelist($data)
    {
        if (!is_array($data)) {
            return [];
        }

        $filtered = [];
        foreach ($this->allowedFields as $field) {
            if (array_key_exists($field, $data)) {
                $filtered[$field] = $data[$field];
            }
        }

        return $filtered;
    }

    private function sanitizeData($data)
    {
        $sanitized = [];

        foreach ($data as $key => $value) {
            if ($value === null) {
                continue;
            }

            if (in_array($key, ['customer_name', 'customer_email', 'status', 'payment_method'], true)) {
                if (is_string($value)) {
                    $sanitized[$key] = $this->sanitizeString($value);
                }
            } elseif ($key === 'total_amount') {
                $sanitized[$key] = (float) $value;
            } elseif ($key === 'version') {
                $sanitized[$key] = (int) $value;
            } else {
                $sanitized[$key] = $value;
            }
        }

        return $sanitized;
    }

    private function sanitizeString($value)
    {
        if (!is_string($value)) {
            return '';
        }
        $value = trim($value);
        $value = strip_tags($value);
        $value = preg_replace('/[\x00-\x1F\x7F]/', '', $value);
        return $value;
    }

    private function jsonResponse(Response $response, $data, $status = 200)
    {
        $response->getBody()->write(json_encode($data, JSON_UNESCAPED_UNICODE));
        return $response->withHeader('Content-Type', 'application/json')->withStatus($status);
    }
}

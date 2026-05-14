<?php

use Slim\Factory\AppFactory;
use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;

require __DIR__ . '/vendor/autoload.php';

require_once __DIR__ . '/OrderController.php';

$app = AppFactory::create();

$app->addBodyParsingMiddleware();
$app->addErrorMiddleware(true, true, true);

$app->options('/{routes:.+}', function (Request $request, Response $response) {
    return $response;
});

$app->add(function (Request $request, $handler) {
    $response = $handler->handle($request);
    return $response
        ->withHeader('Access-Control-Allow-Origin', '*')
        ->withHeader('Access-Control-Allow-Headers', 'Content-Type')
        ->withHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
});

$orderController = new OrderController();

$app->get('/api/orders', [$orderController, 'getAll']);
$app->get('/api/orders/{id}', [$orderController, 'getById']);
$app->post('/api/orders', [$orderController, 'create']);
$app->put('/api/orders/{id}', [$orderController, 'update']);
$app->patch('/api/orders/{id}', [$orderController, 'update']);
$app->delete('/api/orders/{id}', [$orderController, 'delete']);

$app->post('/api/orders/{id}/pay', [$orderController, 'createPayment']);
$app->post('/api/payments/{payment_no}/simulate', [$orderController, 'simulatePay']);
$app->post('/api/payment/callback', [$orderController, 'paymentCallback']);
$app->get('/api/orders/{id}/payment', [$orderController, 'getPaymentStatus']);

$app->post('/api/queue/process-timeout', [$orderController, 'processTimeout']);
$app->post('/api/queue/process-events', [$orderController, 'processQueue']);

$app->get('/', function (Request $request, Response $response) {
    $response->getBody()->write(json_encode([
        'message' => 'Welcome to Order API',
        'endpoints' => [
            'Orders' => [
                'GET    /api/orders'       => 'List all orders',
                'GET    /api/orders/{id}'  => 'Get order by ID',
                'POST   /api/orders'       => 'Create new order',
                'PUT    /api/orders/{id}'  => 'Update order',
                'PATCH  /api/orders/{id}'  => 'Update order',
                'DELETE /api/orders/{id}'  => 'Delete order'
            ],
            'Payments' => [
                'POST   /api/orders/{id}/pay'          => 'Create payment',
                'POST   /api/payments/{payment_no}/simulate' => 'Simulate payment (success/fail)',
                'POST   /api/payment/callback'         => 'Payment callback endpoint',
                'GET    /api/orders/{id}/payment'      => 'Get payment status'
            ],
            'Queue' => [
                'POST   /api/queue/process-timeout'    => 'Process timeout orders (cron)',
                'POST   /api/queue/process-events'     => 'Process event queue (cron)'
            ],
            'Webhook' => [
                'GET    /webhook.php'                  => 'Webhook info',
                'GET    /webhook.php?action=list'      => 'List received events',
                'GET    /webhook.php?action=config'    => 'Get webhook config',
                'POST   /webhook.php?action=config'    => 'Set webhook URL',
                'POST   /webhook.php'                  => 'Receive webhook event'
            ]
        ],
        'order_statuses' => ['pending', 'processing', 'completed', 'cancelled'],
        'payment_timeout_seconds' => 300
    ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    return $response->withHeader('Content-Type', 'application/json');
});

$app->run();

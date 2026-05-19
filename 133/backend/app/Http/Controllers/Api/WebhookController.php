<?php

namespace App\Http\Controllers\Api;

use App\Models\WebhookEndpoint;
use App\Models\WebhookDelivery;
use App\Services\WebhookService;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Validation\ValidationException;

class WebhookController extends Controller
{
    protected $webhookService;
    
    public function __construct(WebhookService $webhookService)
    {
        $this->middleware('auth:tenant');
        $this->webhookService = $webhookService;
    }

    public function index(Request $request)
    {
        $query = WebhookEndpoint::with('creator');
        
        if ($request->filled('is_active')) {
            $query->where('is_active', $request->is_active);
        }
        
        if ($request->filled('event')) {
            $query->where('events', 'like', "%{$request->event}%");
        }
        
        $endpoints = $query->orderBy('created_at', 'desc')->paginate(10);
        
        return response()->json($endpoints);
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'url' => 'required|url|max:1000',
            'method' => 'required|in:POST,PUT,PATCH',
            'headers' => 'nullable|array',
            'events' => 'required|array',
            'events.*' => 'string',
            'is_active' => 'boolean',
            'retry_count' => 'nullable|integer|min:0|max:10',
            'retry_delay' => 'nullable|integer|min:0',
            'timeout' => 'nullable|integer|min:1|max:300',
        ]);

        $endpoint = WebhookEndpoint::create([
            'name' => $request->name,
            'description' => $request->description,
            'url' => $request->url,
            'method' => $request->method,
            'headers' => $request->headers,
            'events' => $request->events,
            'is_active' => $request->is_active ?? true,
            'secret_key' => WebhookEndpoint::generateSecretKey(),
            'retry_count' => $request->retry_count ?? 3,
            'retry_delay' => $request->retry_delay ?? 60,
            'timeout' => $request->timeout ?? 30,
            'created_by' => auth('tenant')->id(),
        ]);

        return response()->json([
            'message' => 'Webhook endpoint created successfully',
            'endpoint' => $endpoint->load('creator'),
        ], 201);
    }

    public function show(WebhookEndpoint $endpoint)
    {
        return response()->json($endpoint->load('creator'));
    }

    public function update(Request $request, WebhookEndpoint $endpoint)
    {
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'description' => 'nullable|string',
            'url' => 'sometimes|url|max:1000',
            'method' => 'sometimes|in:POST,PUT,PATCH',
            'headers' => 'nullable|array',
            'events' => 'sometimes|array',
            'events.*' => 'string',
            'is_active' => 'boolean',
            'retry_count' => 'nullable|integer|min:0|max:10',
            'retry_delay' => 'nullable|integer|min:0',
            'timeout' => 'nullable|integer|min:1|max:300',
        ]);

        $endpoint->update($request->only([
            'name', 'description', 'url', 'method', 'headers', 
            'events', 'is_active', 'retry_count', 'retry_delay', 'timeout'
        ]));

        return response()->json([
            'message' => 'Webhook endpoint updated successfully',
            'endpoint' => $endpoint->load('creator'),
        ]);
    }

    public function destroy(WebhookEndpoint $endpoint)
    {
        $endpoint->delete();
        return response()->json([
            'message' => 'Webhook endpoint deleted successfully',
        ]);
    }

    public function regenerateSecret(WebhookEndpoint $endpoint)
    {
        $newSecret = WebhookEndpoint::generateSecretKey();
        $endpoint->update(['secret_key' => $newSecret]);

        return response()->json([
            'message' => 'Secret key regenerated successfully',
            'endpoint' => $endpoint->load('creator'),
        ]);
    }

    public function deliveries(Request $request)
    {
        $query = WebhookDelivery::with('endpoint');
        
        if ($request->filled('endpoint_id')) {
            $query->where('endpoint_id', $request->endpoint_id);
        }
        
        if ($request->filled('status')) {
            $query->where('status', $request->status);
        }
        
        if ($request->filled('event_type')) {
            $query->where('event_type', $request->event_type);
        }
        
        $deliveries = $query->orderBy('created_at', 'desc')->paginate(20);
        
        return response()->json($deliveries);
    }

    public function showDelivery(WebhookDelivery $delivery)
    {
        return response()->json($delivery->load('endpoint'));
    }

    public function redeliver(WebhookDelivery $delivery)
    {
        $newDelivery = WebhookDelivery::create([
            'endpoint_id' => $delivery->endpoint_id,
            'event_type' => $delivery->event_type,
            'payload' => $delivery->payload,
            'max_attempts' => $delivery->endpoint?->retry_count ?? 3,
            'status' => WebhookDelivery::STATUS_PENDING,
        ]);

        $this->webhookService->processDelivery($newDelivery);

        return response()->json([
            'message' => 'Webhook redelivery initiated successfully',
            'delivery' => $newDelivery->fresh(),
        ]);
    }

    public function testEndpoint(Request $request, WebhookEndpoint $endpoint)
    {
        $request->validate([
            'test_payload' => 'nullable|array',
        ]);

        $payload = $request->test_payload ?? [
            'test' => true,
            'message' => 'This is a test webhook',
            'timestamp' => now()->toISOString(),
        ];

        $delivery = WebhookDelivery::create([
            'endpoint_id' => $endpoint->id,
            'event_type' => 'test',
            'payload' => $payload,
            'max_attempts' => 1,
            'status' => WebhookDelivery::STATUS_PENDING,
        ]);

        $this->webhookService->processDelivery($delivery);

        return response()->json([
            'message' => 'Test webhook sent successfully',
            'delivery' => $delivery->fresh(),
        ]);
    }

    public function getAvailableEvents()
    {
        return response()->json([
            'events' => WebhookEndpoint::getAvailableEvents(),
            'methods' => WebhookEndpoint::getAvailableMethods(),
        ]);
    }

    public function getStats(Request $request)
    {
        $query = WebhookDelivery::query();
        
        if ($request->filled('endpoint_id')) {
            $query->where('endpoint_id', $request->endpoint_id);
        }
        
        $total = $query->count();
        $success = $query->clone()->where('status', WebhookDelivery::STATUS_SUCCESS)->count();
        $failed = $query->clone()->where('status', WebhookDelivery::STATUS_FAILED)->count();
        $pending = $query->clone()->whereIn('status', [WebhookDelivery::STATUS_PENDING, WebhookDelivery::STATUS_RETRYING])->count();

        $successRate = $total > 0 ? round(($success / $total) * 100, 2) : 100;

        return response()->json([
            'total' => $total,
            'success' => $success,
            'failed' => $failed,
            'pending' => $pending,
            'success_rate' => $successRate,
        ]);
    }
}

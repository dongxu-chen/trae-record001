<?php

namespace App\Services;

use App\Models\WebhookEndpoint;
use App\Models\WebhookDelivery;
use App\Models\FormSubmission;
use App\Models\Form;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class WebhookService
{
    public function dispatchEvent(string $eventType, $model, array $additionalData = [])
    {
        $endpoints = WebhookEndpoint::active()
            ->get()
            ->filter(function ($endpoint) use ($eventType) {
                return $endpoint->listensToEvent($eventType);
            });

        foreach ($endpoints as $endpoint) {
            $this->createDelivery($endpoint, $eventType, $model, $additionalData);
        }

        Log::info("Webhook event dispatched", [
            'event_type' => $eventType,
            'endpoint_count' => $endpoints->count(),
        ]);
    }

    protected function createDelivery(WebhookEndpoint $endpoint, string $eventType, $model, array $additionalData)
    {
        $payload = $this->buildPayload($eventType, $model, $additionalData);

        return WebhookDelivery::create([
            'endpoint_id' => $endpoint->id,
            'event_type' => $eventType,
            'payload' => $payload,
            'max_attempts' => $endpoint->retry_count,
            'status' => WebhookDelivery::STATUS_PENDING,
        ]);
    }

    protected function buildPayload(string $eventType, $model, array $additionalData): array
    {
        $basePayload = [
            'event_type' => $eventType,
            'timestamp' => now()->toISOString(),
            'data' => [],
        ];

        if ($model instanceof FormSubmission) {
            $basePayload['data'] = [
                'submission' => $model->toArray(),
                'form' => $model->form ? $model->form->only(['id', 'name', 'description']) : null,
            ];
        } elseif ($model instanceof Form) {
            $basePayload['data'] = [
                'form' => $model->toArray(),
            ];
        }

        return array_merge($basePayload, $additionalData);
    }

    public function processDelivery(WebhookDelivery $delivery): void
    {
        $endpoint = $delivery->endpoint;

        if (!$endpoint || !$endpoint->is_active) {
            $delivery->markAsFailed('Endpoint is inactive or not found');
            return;
        }

        try {
            $headers = array_merge([
                'Content-Type' => 'application/json',
                'X-Webhook-Signature' => $endpoint->generateSignature($delivery->payload),
                'X-Webhook-Event' => $delivery->event_type,
            ], $endpoint->headers ?? []);

            $response = Http::timeout($endpoint->timeout)
                ->withHeaders($headers)
                ->send($endpoint->method, $endpoint->url, [
                    'json' => $delivery->payload,
                ]);

            if ($response->successful()) {
                $delivery->markAsSuccess(
                    $response->status(),
                    $response->body(),
                    $response->headers()
                );

                Log::info("Webhook delivery successful", [
                    'delivery_id' => $delivery->id,
                    'endpoint_id' => $endpoint->id,
                    'event_type' => $delivery->event_type,
                    'status' => $response->status(),
                ]);
            } else {
                $delivery->markAsFailed(
                    "HTTP request failed with status: {$response->status()}",
                    $response->status(),
                    $response->body()
                );

                Log::warning("Webhook delivery failed", [
                    'delivery_id' => $delivery->id,
                    'endpoint_id' => $endpoint->id,
                    'event_type' => $delivery->event_type,
                    'status' => $response->status(),
                ]);
            }
        } catch (\Exception $e) {
            $delivery->markAsFailed($e->getMessage());

            Log::error("Webhook delivery exception", [
                'delivery_id' => $delivery->id,
                'endpoint_id' => $endpoint->id,
                'event_type' => $delivery->event_type,
                'error' => $e->getMessage(),
            ]);
        }
    }

    public function processPendingDeliveries(): int
    {
        $deliveries = WebhookDelivery::needsRetry()
            ->orderBy('created_at', 'asc')
            ->limit(100)
            ->get();

        foreach ($deliveries as $delivery) {
            $this->processDelivery($delivery);
        }

        return $deliveries->count();
    }

    public function dispatchFormSubmitted(FormSubmission $submission): void
    {
        $this->dispatchEvent(WebhookEndpoint::EVENT_FORM_SUBMITTED, $submission);
    }

    public function dispatchSubmissionApproved(FormSubmission $submission, array $approvalData = []): void
    {
        $this->dispatchEvent(WebhookEndpoint::EVENT_SUBMISSION_APPROVED, $submission, [
            'approval' => $approvalData,
        ]);
    }

    public function dispatchSubmissionRejected(FormSubmission $submission, array $approvalData = []): void
    {
        $this->dispatchEvent(WebhookEndpoint::EVENT_SUBMISSION_REJECTED, $submission, [
            'approval' => $approvalData,
        ]);
    }

    public function dispatchFormUpdated(Form $form): void
    {
        $this->dispatchEvent(WebhookEndpoint::EVENT_FORM_UPDATED, $form);
    }
}

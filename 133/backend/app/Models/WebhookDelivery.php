<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class WebhookDelivery extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'endpoint_id',
        'event_type',
        'payload',
        'attempts',
        'max_attempts',
        'status',
        'response_status',
        'response_body',
        'response_headers',
        'error_message',
        'delivered_at',
        'last_attempted_at',
    ];
    
    protected $casts = [
        'payload' => 'array',
        'response_headers' => 'array',
        'attempts' => 'integer',
        'max_attempts' => 'integer',
        'response_status' => 'integer',
        'delivered_at' => 'datetime',
        'last_attempted_at' => 'datetime',
    ];
    
    const STATUS_PENDING = 'pending';
    const STATUS_SUCCESS = 'success';
    const STATUS_FAILED = 'failed';
    const STATUS_RETRYING = 'retrying';
    
    public function endpoint(): BelongsTo
    {
        return $this->belongsTo(WebhookEndpoint::class, 'endpoint_id');
    }
    
    public function scopePending($query)
    {
        return $query->where('status', self::STATUS_PENDING);
    }
    
    public function scopeSuccess($query)
    {
        return $query->where('status', self::STATUS_SUCCESS);
    }
    
    public function scopeFailed($query)
    {
        return $query->where('status', self::STATUS_FAILED);
    }
    
    public function scopeRetrying($query)
    {
        return $query->where('status', self::STATUS_RETRYING);
    }
    
    public function scopeNeedsRetry($query)
    {
        return $query->where(function ($q) {
            $q->where('status', self::STATUS_PENDING)
                ->orWhere('status', self::STATUS_RETRYING);
        })->whereColumn('attempts', '<', 'max_attempts');
    }
    
    public function markAsSuccess($responseStatus, $responseBody, $responseHeaders = null)
    {
        $this->update([
            'status' => self::STATUS_SUCCESS,
            'response_status' => $responseStatus,
            'response_body' => $responseBody,
            'response_headers' => $responseHeaders,
            'attempts' => $this->attempts + 1,
            'delivered_at' => now(),
            'last_attempted_at' => now(),
        ]);
    }
    
    public function markAsFailed($errorMessage, $responseStatus = null, $responseBody = null)
    {
        $this->update([
            'status' => $this->attempts + 1 >= $this->max_attempts ? self::STATUS_FAILED : self::STATUS_RETRYING,
            'error_message' => $errorMessage,
            'response_status' => $responseStatus,
            'response_body' => $responseBody,
            'attempts' => $this->attempts + 1,
            'last_attempted_at' => now(),
        ]);
    }
    
    public function isPending(): bool
    {
        return $this->status === self::STATUS_PENDING;
    }
    
    public function isSuccess(): bool
    {
        return $this->status === self::STATUS_SUCCESS;
    }
    
    public function isFailed(): bool
    {
        return $this->status === self::STATUS_FAILED;
    }
    
    public function canRetry(): bool
    {
        return $this->attempts < $this->max_attempts;
    }
}

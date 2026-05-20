<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class WebhookEndpoint extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'name',
        'description',
        'url',
        'method',
        'headers',
        'events',
        'is_active',
        'secret_key',
        'retry_count',
        'retry_delay',
        'timeout',
        'created_by',
    ];
    
    protected $casts = [
        'headers' => 'array',
        'events' => 'array',
        'is_active' => 'boolean',
        'retry_count' => 'integer',
        'retry_delay' => 'integer',
        'timeout' => 'integer',
    ];
    
    protected $hidden = [
        'secret_key',
    ];
    
    const METHOD_POST = 'POST';
    const METHOD_PUT = 'PUT';
    const METHOD_PATCH = 'PATCH';
    
    const EVENT_FORM_SUBMITTED = 'form.submitted';
    const EVENT_FORM_UPDATED = 'form.updated';
    const EVENT_SUBMISSION_APPROVED = 'submission.approved';
    const EVENT_SUBMISSION_REJECTED = 'submission.rejected';
    
    public static function getAvailableEvents(): array
    {
        return [
            self::EVENT_FORM_SUBMITTED => 'Form Submitted',
            self::EVENT_FORM_UPDATED => 'Form Updated',
            self::EVENT_SUBMISSION_APPROVED => 'Submission Approved',
            self::EVENT_SUBMISSION_REJECTED => 'Submission Rejected',
        ];
    }
    
    public static function getAvailableMethods(): array
    {
        return [
            self::METHOD_POST => 'POST',
            self::METHOD_PUT => 'PUT',
            self::METHOD_PATCH => 'PATCH',
        ];
    }
    
    public function deliveries(): HasMany
    {
        return $this->hasMany(WebhookDelivery::class, 'endpoint_id');
    }
    
    public function creator()
    {
        return $this->belongsTo(TenantUser::class, 'created_by');
    }
    
    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }
    
    public function scopeForEvent($query, $event)
    {
        return $query->where('events', 'like', "%{$event}%");
    }
    
    public function listensToEvent($event): bool
    {
        return in_array($event, $this->events ?? []);
    }
    
    public function generateSignature($payload): string
    {
        return hash_hmac('sha256', json_encode($payload), $this->secret_key);
    }
    
    public static function generateSecretKey(): string
    {
        return 'whsec_' . bin2hex(random_bytes(32));
    }
    
    public function getSuccessRateAttribute(): float
    {
        $total = $this->deliveries()->count();
        if ($total === 0) {
            return 100.0;
        }
        
        $success = $this->deliveries()->where('status', WebhookDelivery::STATUS_SUCCESS)->count();
        return round(($success / $total) * 100, 2);
    }
    
    public function getLastDeliveryAtAttribute()
    {
        return $this->deliveries()->latest('created_at')->value('created_at');
    }
}

<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TenantUsageLog extends Model
{
    protected $connection = 'central';
    
    protected $fillable = [
        'tenant_id',
        'period_type',
        'period_start',
        'period_end',
        'forms_count',
        'submissions_count',
        'users_count',
        'storage_used',
        'api_calls_count',
        'webhook_calls_count',
    ];
    
    protected $casts = [
        'period_start' => 'datetime',
        'period_end' => 'datetime',
        'forms_count' => 'integer',
        'submissions_count' => 'integer',
        'users_count' => 'integer',
        'storage_used' => 'integer',
        'api_calls_count' => 'integer',
        'webhook_calls_count' => 'integer',
    ];
    
    const PERIOD_DAILY = 'daily';
    const PERIOD_WEEKLY = 'weekly';
    const PERIOD_MONTHLY = 'monthly';
    
    public function tenant(): BelongsTo
    {
        return $this->belongsTo(Tenant::class);
    }
    
    public function scopeForTenant($query, $tenantId)
    {
        return $query->where('tenant_id', $tenantId);
    }
    
    public function scopeByPeriodType($query, $periodType)
    {
        return $query->where('period_type', $periodType);
    }
    
    public function scopeCurrentPeriod($query, $periodType = null)
    {
        $query->orderBy('period_end', 'desc');
        
        if ($periodType) {
            $query->where('period_type', $periodType);
        }
        
        return $query;
    }
    
    public function getTotalUsageAttribute(): int
    {
        return $this->forms_count + $this->submissions_count + $this->api_calls_count;
    }
}

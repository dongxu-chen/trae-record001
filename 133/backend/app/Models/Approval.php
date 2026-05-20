<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Approval extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'submission_id',
        'step_id',
        'approver_id',
        'step_order',
        'status',
        'comment',
        'approved_at',
    ];
    
    protected $casts = [
        'approved_at' => 'datetime',
    ];
    
    const STATUS_PENDING = 'pending';
    const STATUS_APPROVED = 'approved';
    const STATUS_REJECTED = 'rejected';
    const STATUS_WAITING = 'waiting';
    const STATUS_CANCELLED = 'cancelled';
    
    public function submission()
    {
        return $this->belongsTo(FormSubmission::class);
    }
    
    public function approver()
    {
        return $this->belongsTo(TenantUser::class, 'approver_id');
    }
    
    public function step()
    {
        return $this->belongsTo(ApprovalStep::class, 'step_id');
    }
    
    public function isPending()
    {
        return $this->status === self::STATUS_PENDING;
    }
    
    public function isApproved()
    {
        return $this->status === self::STATUS_APPROVED;
    }
    
    public function isRejected()
    {
        return $this->status === self::STATUS_REJECTED;
    }
    
    public function scopeForStep($query, $stepId)
    {
        return $query->where('step_id', $stepId);
    }
    
    public function scopeByStatus($query, $status)
    {
        return $query->where('status', $status);
    }
}

<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ApprovalStep extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'approval_flow_id',
        'name',
        'order',
        'approver_id',
        'approver_role',
        'approval_type',
        'approval_mode',
        'approve_threshold',
        'approver_ids',
    ];
    
    protected $casts = [
        'approver_ids' => 'array',
        'approve_threshold' => 'integer',
    ];
    
    const APPROVAL_TYPE_PERSON = 'person';
    const APPROVAL_TYPE_ROLE = 'role';
    const APPROVAL_TYPE_MULTI = 'multi';
    
    const APPROVAL_MODE_ALL = 'all';
    const APPROVAL_MODE_ANY = 'any';
    const APPROVAL_MODE_THRESHOLD = 'threshold';
    
    public function flow()
    {
        return $this->belongsTo(ApprovalFlow::class);
    }
    
    public function approver()
    {
        return $this->belongsTo(TenantUser::class, 'approver_id');
    }
    
    public function approvers()
    {
        if ($this->approval_type === self::APPROVAL_TYPE_MULTI && !empty($this->approver_ids)) {
            return TenantUser::whereIn('id', $this->approver_ids)->get();
        }
        
        if ($this->approval_type === self::APPROVAL_TYPE_ROLE && $this->approver_role) {
            return TenantUser::where('role', $this->approver_role)->get();
        }
        
        return collect([$this->approver])->filter();
    }
    
    public function getApproverCountAttribute()
    {
        return $this->approvers()->count();
    }
    
    public function isAllMode()
    {
        return $this->approval_mode === self::APPROVAL_MODE_ALL;
    }
    
    public function isAnyMode()
    {
        return $this->approval_mode === self::APPROVAL_MODE_ANY;
    }
    
    public function isThresholdMode()
    {
        return $this->approval_mode === self::APPROVAL_MODE_THRESHOLD;
    }
}

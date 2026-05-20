<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FormSubmission extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'form_id',
        'data',
        'submitted_by',
        'status',
    ];

    protected $casts = [
        'data' => 'array',
    ];

    public function form()
    {
        return $this->belongsTo(Form::class);
    }

    public function submitter()
    {
        return $this->belongsTo(TenantUser::class, 'submitted_by');
    }

    public function approvals()
    {
        return $this->hasMany(Approval::class, 'submission_id');
    }

    public function currentApprovalStep()
    {
        return $this->hasOne(Approval::class, 'submission_id')
            ->where('status', 'pending')
            ->orderBy('step_order', 'asc');
    }
}

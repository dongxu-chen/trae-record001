<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Tymon\JWTAuth\Contracts\JWTSubject;

class TenantUser extends Authenticatable implements JWTSubject
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'name',
        'email',
        'password',
        'role',
        'is_active',
    ];

    protected $hidden = [
        'password',
        'remember_token',
    ];

    protected $casts = [
        'email_verified_at' => 'datetime',
        'is_active' => 'boolean',
    ];

    public function getJWTIdentifier()
    {
        return $this->getKey();
    }

    public function getJWTCustomClaims()
    {
        return [];
    }

    public function forms()
    {
        return $this->hasMany(Form::class, 'created_by');
    }

    public function submissions()
    {
        return $this->hasMany(FormSubmission::class, 'submitted_by');
    }

    public function approvals()
    {
        return $this->hasMany(Approval::class, 'approver_id');
    }
}

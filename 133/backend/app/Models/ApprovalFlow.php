<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ApprovalFlow extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'name',
        'description',
        'is_active',
    ];

    protected $casts = [
        'is_active' => 'boolean',
    ];

    public function steps()
    {
        return $this->hasMany(ApprovalStep::class)->orderBy('order', 'asc');
    }

    public function forms()
    {
        return $this->hasMany(Form::class);
    }
}

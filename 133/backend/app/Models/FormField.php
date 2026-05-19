<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FormField extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'form_id',
        'label',
        'name',
        'type',
        'options',
        'is_required',
        'order',
        'validation',
    ];

    protected $casts = [
        'options' => 'array',
        'is_required' => 'boolean',
        'validation' => 'array',
    ];

    public function form()
    {
        return $this->belongsTo(Form::class);
    }
}

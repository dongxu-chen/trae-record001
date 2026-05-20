<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class FormVersion extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'form_id',
        'version_number',
        'name',
        'description',
        'schema',
        'fields',
        'created_by',
        'is_current',
        'change_note',
    ];
    
    protected $casts = [
        'schema' => 'array',
        'fields' => 'array',
        'is_current' => 'boolean',
    ];
    
    public function form(): BelongsTo
    {
        return $this->belongsTo(Form::class);
    }
    
    public function creator(): BelongsTo
    {
        return $this->belongsTo(TenantUser::class, 'created_by');
    }
    
    public function scopeOrdered($query)
    {
        return $query->orderBy('version_number', 'desc');
    }
    
    public function scopeCurrent($query)
    {
        return $query->where('is_current', true);
    }
    
    public function getRouteKeyName()
    {
        return 'id';
    }
    
    protected static function boot()
    {
        parent::boot();
        
        static::creating(function ($version) {
            if (empty($version->version_number)) {
                $maxVersion = static::where('form_id', $version->form_id)
                    ->max('version_number');
                $version->version_number = $maxVersion ? $maxVersion + 1 : 1;
            }
            
            if ($version->is_current) {
                static::where('form_id', $version->form_id)
                    ->where('id', '!=', $version->id)
                    ->update(['is_current' => false]);
            }
        });
    }
}

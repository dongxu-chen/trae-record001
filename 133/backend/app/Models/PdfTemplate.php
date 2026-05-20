<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class PdfTemplate extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'form_id',
        'name',
        'description',
        'template_html',
        'template_css',
        'page_settings',
        'is_default',
        'is_active',
        'created_by',
    ];
    
    protected $casts = [
        'page_settings' => 'array',
        'is_default' => 'boolean',
        'is_active' => 'boolean',
    ];
    
    public function form(): BelongsTo
    {
        return $this->belongsTo(Form::class);
    }
    
    public function creator(): BelongsTo
    {
        return $this->belongsTo(TenantUser::class, 'created_by');
    }
    
    public function printJobs(): HasMany
    {
        return $this->hasMany(PdfPrintJob::class);
    }
    
    public function scopeActive($query)
    {
        return $query->where('is_active', true);
    }
    
    public function scopeDefault($query)
    {
        return $query->where('is_default', true);
    }
    
    public function scopeForForm($query, $formId)
    {
        return $query->where('form_id', $formId);
    }
    
    protected static function boot()
    {
        parent::boot();
        
        static::creating(function ($template) {
            if ($template->is_default) {
                static::where('form_id', $template->form_id)
                    ->where('id', '!=', $template->id)
                    ->update(['is_default' => false]);
            }
        });
        
        static::updating(function ($template) {
            if ($template->is_default) {
                static::where('form_id', $template->form_id)
                    ->where('id', '!=', $template->id)
                    ->update(['is_default' => false]);
            }
        });
    }
    
    public function getDefaultPageSettings(): array
    {
        return [
            'size' => 'A4',
            'orientation' => 'portrait',
            'margin' => [
                'top' => 20,
                'right' => 20,
                'bottom' => 20,
                'left' => 20,
            ],
            'header_height' => 50,
            'footer_height' => 50,
        ];
    }
    
    public function getPageSettingsAttribute($value): array
    {
        $settings = json_decode($value, true) ?? [];
        return array_merge($this->getDefaultPageSettings(), $settings);
    }
    
    public function renderForSubmission(FormSubmission $submission): string
    {
        $html = $this->template_html;
        $data = $submission->data ?? [];
        
        foreach ($data as $key => $value) {
            $placeholder = "{{{$key}}}";
            
            if (is_array($value)) {
                $value = implode(', ', $value);
            }
            
            $html = str_replace($placeholder, htmlspecialchars($value ?? ''), $html);
        }
        
        $html = str_replace('{{submission_id}}', $submission->id, $html);
        $html = str_replace('{{submitted_at}}', $submission->created_at->format('Y-m-d H:i:s'), $html);
        $html = str_replace('{{form_name}}', $this->form->name ?? '', $html);
        
        return $html;
    }
}

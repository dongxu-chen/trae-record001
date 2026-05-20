<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PdfPrintJob extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'template_id',
        'submission_id',
        'created_by',
        'status',
        'file_path',
        'file_size',
        'page_count',
        'error_message',
        'printed_at',
    ];
    
    protected $casts = [
        'page_count' => 'integer',
        'file_size' => 'integer',
        'printed_at' => 'datetime',
    ];
    
    const STATUS_PENDING = 'pending';
    const STATUS_PROCESSING = 'processing';
    const STATUS_COMPLETED = 'completed';
    const STATUS_FAILED = 'failed';
    
    public function template(): BelongsTo
    {
        return $this->belongsTo(PdfTemplate::class, 'template_id');
    }
    
    public function submission(): BelongsTo
    {
        return $this->belongsTo(FormSubmission::class, 'submission_id');
    }
    
    public function creator(): BelongsTo
    {
        return $this->belongsTo(TenantUser::class, 'created_by');
    }
    
    public function scopePending($query)
    {
        return $query->where('status', self::STATUS_PENDING);
    }
    
    public function scopeCompleted($query)
    {
        return $query->where('status', self::STATUS_COMPLETED);
    }
    
    public function scopeFailed($query)
    {
        return $query->where('status', self::STATUS_FAILED);
    }
    
    public function markAsProcessing()
    {
        $this->update(['status' => self::STATUS_PROCESSING]);
    }
    
    public function markAsCompleted($filePath, $fileSize, $pageCount = 1)
    {
        $this->update([
            'status' => self::STATUS_COMPLETED,
            'file_path' => $filePath,
            'file_size' => $fileSize,
            'page_count' => $pageCount,
            'printed_at' => now(),
        ]);
    }
    
    public function markAsFailed($errorMessage)
    {
        $this->update([
            'status' => self::STATUS_FAILED,
            'error_message' => $errorMessage,
        ]);
    }
    
    public function isPending(): bool
    {
        return $this->status === self::STATUS_PENDING;
    }
    
    public function isCompleted(): bool
    {
        return $this->status === self::STATUS_COMPLETED;
    }
    
    public function isFailed(): bool
    {
        return $this->status === self::STATUS_FAILED;
    }
}

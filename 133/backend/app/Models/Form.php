<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Form extends Model
{
    protected $connection = 'tenant';
    
    protected $fillable = [
        'name',
        'description',
        'schema',
        'is_published',
        'created_by',
        'approval_flow_id',
    ];

    protected $casts = [
        'schema' => 'array',
        'is_published' => 'boolean',
    ];

    public function creator()
    {
        return $this->belongsTo(TenantUser::class, 'created_by');
    }

    public function fields()
    {
        return $this->hasMany(FormField::class);
    }

    public function submissions()
    {
        return $this->hasMany(FormSubmission::class);
    }

    public function approvalFlow()
    {
        return $this->belongsTo(ApprovalFlow::class);
    }

    public function versions(): HasMany
    {
        return $this->hasMany(FormVersion::class)->ordered();
    }

    public function currentVersion()
    {
        return $this->hasOne(FormVersion::class)->current();
    }

    public function createVersion($userId, $changeNote = null): FormVersion
    {
        $fieldsData = $this->fields->map(function ($field) {
            return $field->only([
                'label', 'name', 'type', 'options', 'is_required', 'order', 'validation'
            ]);
        })->toArray();

        return FormVersion::create([
            'form_id' => $this->id,
            'name' => $this->name,
            'description' => $this->description,
            'schema' => $this->schema,
            'fields' => $fieldsData,
            'created_by' => $userId,
            'is_current' => true,
            'change_note' => $changeNote,
        ]);
    }

    public function rollbackToVersion($versionId, $userId): FormVersion
    {
        $version = FormVersion::where('form_id', $this->id)
            ->where('id', $versionId)
            ->firstOrFail();

        $this->update([
            'name' => $version->name,
            'description' => $version->description,
            'schema' => $version->schema,
        ]);

        $this->fields()->delete();
        
        foreach ($version->fields as $fieldData) {
            $this->fields()->create($fieldData);
        }

        return $this->createVersion($userId, "Rolled back to version {$version->version_number}");
    }

    public function getLatestVersionNumber(): int
    {
        return FormVersion::where('form_id', $this->id)->max('version_number') ?? 0;
    }
}

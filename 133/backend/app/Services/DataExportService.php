<?php

namespace App\Services;

use App\Models\FormSubmission;
use App\Models\Form;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class DataExportService
{
    const CHUNK_SIZE = 100;
    
    public function exportToCsv(Form $form, callable $streamCallback)
    {
        $fields = $form->fields()->orderBy('order', 'asc')->get();
        $fieldNames = $fields->pluck('name')->toArray();
        $fieldLabels = $fields->pluck('label')->toArray();
        
        $headers = array_merge(
            ['Submission ID', 'Submitted At', 'Submitter Name', 'Submitter Email', 'Status'],
            $fieldLabels
        );
        
        $streamCallback($this->arrayToCsvLine($headers));
        
        $count = 0;
        FormSubmission::where('form_id', $form->id)
            ->with('submitter')
            ->orderBy('created_at', 'desc')
            ->chunk(self::CHUNK_SIZE, function ($submissions) use ($fieldNames, $streamCallback, &$count) {
                foreach ($submissions as $submission) {
                    $row = [
                        $submission->id,
                        $submission->created_at->toDateTimeString(),
                        $submission->submitter?->name ?? 'N/A',
                        $submission->submitter?->email ?? 'N/A',
                        $submission->status,
                    ];
                    
                    $data = $submission->data ?? [];
                    foreach ($fieldNames as $fieldName) {
                        $value = $data[$fieldName] ?? '';
                        if (is_array($value)) {
                            $value = implode('; ', $value);
                        }
                        $row[] = $value;
                    }
                    
                    $streamCallback($this->arrayToCsvLine($row));
                    $count++;
                }
                
                Log::debug("Exported {$count} submissions so far");
            });
        
        return $count;
    }
    
    public function exportToJson(Form $form, callable $streamCallback)
    {
        $isFirst = true;
        $streamCallback("[\n");
        
        $count = 0;
        FormSubmission::where('form_id', $form->id)
            ->with('submitter')
            ->orderBy('created_at', 'desc')
            ->chunk(self::CHUNK_SIZE, function ($submissions) use (&$isFirst, $streamCallback, &$count) {
                foreach ($submissions as $submission) {
                    if (!$isFirst) {
                        $streamCallback(",\n");
                    }
                    
                    $data = [
                        'id' => $submission->id,
                        'submitted_at' => $submission->created_at->toDateTimeString(),
                        'submitter' => $submission->submitter ? [
                            'id' => $submission->submitter->id,
                            'name' => $submission->submitter->name,
                            'email' => $submission->submitter->email,
                        ] : null,
                        'status' => $submission->status,
                        'data' => $submission->data ?? new \stdClass(),
                    ];
                    
                    $streamCallback(json_encode($data, JSON_PRETTY_PRINT));
                    $isFirst = false;
                    $count++;
                }
                
                Log::debug("Exported {$count} submissions so far");
            });
        
        $streamCallback("\n]");
        
        return $count;
    }
    
    public function exportAllSubmissionsToCsv(array $filters = [], callable $streamCallback)
    {
        $headers = ['Form ID', 'Form Name', 'Submission ID', 'Submitted At', 'Submitter Name', 'Submitter Email', 'Status', 'Data'];
        $streamCallback($this->arrayToCsvLine($headers));
        
        $query = FormSubmission::with('form', 'submitter')->orderBy('created_at', 'desc');
        
        if (isset($filters['status'])) {
            $query->where('status', $filters['status']);
        }
        
        if (isset($filters['start_date'])) {
            $query->where('created_at', '>=', $filters['start_date']);
        }
        
        if (isset($filters['end_date'])) {
            $query->where('created_at', '<=', $filters['end_date']);
        }
        
        $count = 0;
        $query->chunk(self::CHUNK_SIZE, function ($submissions) use ($streamCallback, &$count) {
            foreach ($submissions as $submission) {
                $row = [
                    $submission->form?->id ?? 'N/A',
                    $submission->form?->name ?? 'N/A',
                    $submission->id,
                    $submission->created_at->toDateTimeString(),
                    $submission->submitter?->name ?? 'N/A',
                    $submission->submitter?->email ?? 'N/A',
                    $submission->status,
                    json_encode($submission->data ?? new \stdClass()),
                ];
                
                $streamCallback($this->arrayToCsvLine($row));
                $count++;
            }
        });
        
        return $count;
    }
    
    protected function arrayToCsvLine(array $fields): string
    {
        $output = '';
        $handle = fopen('php://temp', 'r+');
        
        fputcsv($handle, $fields);
        rewind($handle);
        $output = fgets($handle);
        fclose($handle);
        
        return $output;
    }
    
    public function getExportFilename(Form $form, string $format = 'csv'): string
    {
        $slug = Str::slug($form->name);
        $date = now()->format('Y-m-d-His');
        return "{$slug}-export-{$date}.{$format}";
    }
    
    public function getExportStats(Form $form): array
    {
        $total = FormSubmission::where('form_id', $form->id)->count();
        $approved = FormSubmission::where('form_id', $form->id)->where('status', 'approved')->count();
        $pending = FormSubmission::where('form_id', $form->id)->where('status', 'pending_approval')->count();
        $rejected = FormSubmission::where('form_id', $form->id)->where('status', 'rejected')->count();
        
        return [
            'total' => $total,
            'approved' => $approved,
            'pending' => $pending,
            'rejected' => $rejected,
            'estimated_size_kb' => $total * 2,
        ];
    }
}

<?php

namespace App\Http\Controllers\Api;

use App\Models\Form;
use App\Models\PdfTemplate;
use App\Models\PdfPrintJob;
use App\Models\FormSubmission;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\ValidationException;

class PdfTemplateController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth:tenant');
    }

    public function index(Request $request)
    {
        $query = PdfTemplate::with('form', 'creator');
        
        if ($request->filled('form_id')) {
            $query->where('form_id', $request->form_id);
        }
        
        if ($request->filled('is_active')) {
            $query->where('is_active', $request->is_active);
        }
        
        $templates = $query->orderBy('created_at', 'desc')->paginate(10);
        
        return response()->json($templates);
    }

    public function store(Request $request)
    {
        $request->validate([
            'form_id' => 'required|exists:forms,id',
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'template_html' => 'required|string',
            'template_css' => 'nullable|string',
            'page_settings' => 'nullable|array',
            'is_default' => 'boolean',
            'is_active' => 'boolean',
        ]);

        $template = PdfTemplate::create([
            'form_id' => $request->form_id,
            'name' => $request->name,
            'description' => $request->description,
            'template_html' => $request->template_html,
            'template_css' => $request->template_css,
            'page_settings' => $request->page_settings,
            'is_default' => $request->is_default ?? false,
            'is_active' => $request->is_active ?? true,
            'created_by' => auth('tenant')->id(),
        ]);

        return response()->json([
            'message' => 'PDF template created successfully',
            'template' => $template->load('form', 'creator'),
        ], 201);
    }

    public function show(PdfTemplate $template)
    {
        return response()->json($template->load('form', 'creator'));
    }

    public function update(Request $request, PdfTemplate $template)
    {
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'description' => 'nullable|string',
            'template_html' => 'sometimes|string',
            'template_css' => 'nullable|string',
            'page_settings' => 'nullable|array',
            'is_default' => 'boolean',
            'is_active' => 'boolean',
        ]);

        $template->update($request->only([
            'name', 'description', 'template_html', 'template_css', 
            'page_settings', 'is_default', 'is_active'
        ]));

        return response()->json([
            'message' => 'PDF template updated successfully',
            'template' => $template->load('form', 'creator'),
        ]);
    }

    public function destroy(PdfTemplate $template)
    {
        $template->delete();
        return response()->json([
            'message' => 'PDF template deleted successfully',
        ]);
    }

    public function getDefaultTemplate(Form $form)
    {
        $template = PdfTemplate::where('form_id', $form->id)
            ->default()
            ->active()
            ->first();

        if (!$template) {
            $template = PdfTemplate::where('form_id', $form->id)
                ->active()
                ->orderBy('is_default', 'desc')
                ->first();
        }

        return response()->json($template);
    }

    public function preview(Request $request, PdfTemplate $template)
    {
        $request->validate([
            'submission_id' => 'nullable|exists:form_submissions,id',
        ]);

        $html = $template->template_html;
        $css = $template->template_css;
        
        if ($request->filled('submission_id')) {
            $submission = FormSubmission::findOrFail($request->submission_id);
            $html = $template->renderForSubmission($submission);
        }

        return response()->json([
            'html' => $html,
            'css' => $css,
            'page_settings' => $template->page_settings,
        ]);
    }

    public function generatePdf(Request $request, PdfTemplate $template)
    {
        $request->validate([
            'submission_id' => 'required|exists:form_submissions,id',
        ]);

        $submission = FormSubmission::findOrFail($request->submission_id);
        
        $printJob = PdfPrintJob::create([
            'template_id' => $template->id,
            'submission_id' => $submission->id,
            'created_by' => auth('tenant')->id(),
            'status' => PdfPrintJob::STATUS_PENDING,
        ]);

        $printJob->markAsProcessing();

        try {
            $html = $template->renderForSubmission($submission);
            
            $fileName = "pdf/{$template->form_id}/submission_{$submission->id}_" . time() . ".pdf";
            
            $pdfContent = $this->generatePdfContent($html, $template->template_css, $template->page_settings);
            
            Storage::put($fileName, $pdfContent);
            
            $printJob->markAsCompleted(
                $fileName,
                strlen($pdfContent),
                1
            );

            return response()->json([
                'message' => 'PDF generated successfully',
                'print_job' => $printJob->fresh(),
                'download_url' => Storage::url($fileName),
            ]);
        } catch (\Exception $e) {
            $printJob->markAsFailed($e->getMessage());
            
            return response()->json([
                'message' => 'PDF generation failed',
                'error' => $e->getMessage(),
            ], 500);
        }
    }

    protected function generatePdfContent($html, $css, $pageSettings)
    {
        $fullHtml = <<<HTML
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        $css
    </style>
</head>
<body>
    $html
</body>
</html>
HTML;

        return $fullHtml;
    }

    public function downloadPdf(PdfPrintJob $printJob)
    {
        if (!$printJob->isCompleted() || !$printJob->file_path) {
            throw ValidationException::withMessages([
                'job' => 'PDF is not ready for download',
            ]);
        }

        if (!Storage::exists($printJob->file_path)) {
            throw ValidationException::withMessages([
                'job' => 'PDF file not found',
            ]);
        }

        return Storage::download($printJob->file_path);
    }

    public function printJobs(Request $request)
    {
        $query = PdfPrintJob::with('template', 'submission', 'creator');
        
        if ($request->filled('template_id')) {
            $query->where('template_id', $request->template_id);
        }
        
        if ($request->filled('status')) {
            $query->where('status', $request->status);
        }
        
        $jobs = $query->orderBy('created_at', 'desc')->paginate(10);
        
        return response()->json($jobs);
    }
}

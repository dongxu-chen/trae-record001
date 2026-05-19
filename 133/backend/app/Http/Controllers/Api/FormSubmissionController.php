<?php

namespace App\Http\Controllers\Api;

use App\Models\Form;
use App\Models\FormSubmission;
use App\Models\Approval;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use App\Services\FormValidationService;
use App\Services\ApprovalEngine;
use App\Services\DataExportService;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\StreamedResponse;

class FormSubmissionController extends Controller
{
    protected $validationService;
    protected $approvalEngine;
    protected $exportService;
    
    public function __construct(
        FormValidationService $validationService,
        ApprovalEngine $approvalEngine,
        DataExportService $exportService
    ) {
        $this->middleware('auth:tenant');
        $this->validationService = $validationService;
        $this->approvalEngine = $approvalEngine;
        $this->exportService = $exportService;
    }
    
    public function index(Request $request)
    {
        $query = FormSubmission::with('form', 'submitter', 'approvals.approver');
        
        if ($request->filled('form_id')) {
            $query->where('form_id', $request->form_id);
        }
        
        if ($request->filled('status')) {
            $query->where('status', $request->status);
        }
        
        $submissions = $query->orderBy('created_at', 'desc')->paginate(10);
        
        return response()->json($submissions);
    }
    
    public function store(Request $request, Form $form)
    {
        $request->validate([
            'data' => 'required|array',
        ]);
        
        $this->validationService->validateSubmission($form, $request->data);
        
        DB::connection('tenant')->beginTransaction();
        
        try {
            $submission = FormSubmission::create([
                'form_id' => $form->id,
                'data' => $request->data,
                'submitted_by' => auth('tenant')->id(),
                'status' => $form->approval_flow_id ? 'pending_approval' : 'approved',
            ]);
            
            if ($form->approval_flow_id) {
                $this->approvalEngine->initializeApprovals($submission, $form->approvalFlow);
            }
            
            DB::connection('tenant')->commit();
            
            return response()->json([
                'message' => 'Form submitted successfully',
                'submission' => $submission->load('form', 'approvals'),
            ], 201);
        } catch (\Exception $e) {
            DB::connection('tenant')->rollBack();
            throw $e;
        }
    }
    
    public function show(FormSubmission $submission)
    {
        return response()->json($submission->load('form', 'submitter', 'approvals.approver'));
    }
    
    public function export(Request $request)
    {
        $request->validate([
            'form_id' => 'required|exists:forms,id',
            'format' => 'required|in:csv,json',
        ]);
        
        $form = Form::findOrFail($request->form_id);
        $format = $request->format;
        $filename = $this->exportService->getExportFilename($form, $format);
        
        $headers = [
            'Cache-Control' => 'must-revalidate, post-check=0, pre-check=0',
            'Content-type' => $format === 'csv' ? 'text/csv' : 'application/json',
            'Content-Transfer-Encoding' => 'binary',
            'Expires' => '0',
            'Pragma' => 'public',
        ];
        
        $response = new StreamedResponse(function () use ($form, $format) {
            $outputStream = fopen('php://output', 'w');
            
            $callback = function ($data) use ($outputStream) {
                fwrite($outputStream, $data);
                flush();
            };
            
            if ($format === 'csv') {
                $this->exportService->exportToCsv($form, $callback);
            } else {
                $this->exportService->exportToJson($form, $callback);
            }
            
            fclose($outputStream);
        }, 200, $headers);
        
        $response->headers->set('Content-Disposition', "attachment; filename={$filename}");
        
        return $response;
    }
    
    public function exportStats(Request $request)
    {
        $request->validate([
            'form_id' => 'required|exists:forms,id',
        ]);
        
        $form = Form::findOrFail($request->form_id);
        $stats = $this->exportService->getExportStats($form);
        
        return response()->json([
            'form' => $form->only(['id', 'name']),
            'stats' => $stats,
        ]);
    }
}

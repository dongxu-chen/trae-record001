<?php

namespace App\Http\Controllers\Api;

use App\Models\ApprovalFlow;
use App\Models\ApprovalStep;
use App\Models\Approval;
use App\Models\FormSubmission;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use App\Services\ApprovalEngine;
use Illuminate\Support\Facades\DB;

class ApprovalController extends Controller
{
    protected $approvalEngine;
    
    public function __construct(ApprovalEngine $approvalEngine)
    {
        $this->middleware('auth:tenant');
        $this->approvalEngine = $approvalEngine;
    }
    
    public function flows()
    {
        $flows = ApprovalFlow::with('steps.approver')->paginate(10);
        return response()->json($flows);
    }
    
    public function storeFlow(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'steps' => 'required|array',
            'steps.*.name' => 'required|string',
            'steps.*.approval_type' => 'required|in:person,role,multi',
            'steps.*.approval_mode' => 'required|in:all,any,threshold',
            'steps.*.approver_id' => 'nullable|exists:tenant_users,id',
            'steps.*.approver_role' => 'nullable|string',
            'steps.*.approver_ids' => 'nullable|array',
            'steps.*.approve_threshold' => 'nullable|integer|min:1',
        ]);
        
        DB::connection('tenant')->beginTransaction();
        
        try {
            $flow = ApprovalFlow::create([
                'name' => $request->name,
                'description' => $request->description,
                'is_active' => true,
            ]);
            
            foreach ($request->steps as $index => $step) {
                ApprovalStep::create([
                    'approval_flow_id' => $flow->id,
                    'name' => $step['name'],
                    'order' => $index + 1,
                    'approver_id' => $step['approver_id'] ?? null,
                    'approver_role' => $step['approver_role'] ?? null,
                    'approval_type' => $step['approval_type'] ?? 'person',
                    'approval_mode' => $step['approval_mode'] ?? 'all',
                    'approver_ids' => $step['approver_ids'] ?? null,
                    'approve_threshold' => $step['approve_threshold'] ?? null,
                ]);
            }
            
            DB::connection('tenant')->commit();
            
            return response()->json([
                'message' => 'Approval flow created successfully',
                'flow' => $flow->load('steps'),
            ], 201);
        } catch (\Exception $e) {
            DB::connection('tenant')->rollBack();
            throw $e;
        }
    }
    
    public function showFlow(ApprovalFlow $flow)
    {
        return response()->json($flow->load('steps.approver', 'forms'));
    }
    
    public function updateFlow(Request $request, ApprovalFlow $flow)
    {
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'description' => 'nullable|string',
            'is_active' => 'sometimes|boolean',
            'steps' => 'sometimes|array',
        ]);
        
        DB::connection('tenant')->beginTransaction();
        
        try {
            $flow->update($request->only(['name', 'description', 'is_active']));
            
            if ($request->has('steps')) {
                $flow->steps()->delete();
                
                foreach ($request->steps as $index => $step) {
                    ApprovalStep::create([
                        'approval_flow_id' => $flow->id,
                        'name' => $step['name'],
                        'order' => $index + 1,
                        'approver_id' => $step['approver_id'] ?? null,
                        'approver_role' => $step['approver_role'] ?? null,
                        'approval_type' => $step['approval_type'] ?? 'person',
                        'approval_mode' => $step['approval_mode'] ?? 'all',
                        'approver_ids' => $step['approver_ids'] ?? null,
                        'approve_threshold' => $step['approve_threshold'] ?? null,
                    ]);
                }
            }
            
            DB::connection('tenant')->commit();
            
            return response()->json([
                'message' => 'Approval flow updated successfully',
                'flow' => $flow->load('steps'),
            ]);
        } catch (\Exception $e) {
            DB::connection('tenant')->rollBack();
            throw $e;
        }
    }
    
    public function deleteFlow(ApprovalFlow $flow)
    {
        $flow->delete();
        return response()->json([
            'message' => 'Approval flow deleted successfully',
        ]);
    }
    
    public function myApprovals()
    {
        $approvals = Approval::with('submission.form', 'submission.submitter', 'step')
            ->where('approver_id', auth('tenant')->id())
            ->whereIn('status', [Approval::STATUS_PENDING, Approval::STATUS_WAITING])
            ->orderBy('step_order', 'asc')
            ->paginate(10);
        
        return response()->json($approvals);
    }
    
    public function approve(Request $request, Approval $approval)
    {
        if (!$this->approvalEngine->canUserApprove($approval, auth('tenant')->id())) {
            return response()->json(['message' => 'Unauthorized or approval not pending'], 403);
        }
        
        try {
            $this->approvalEngine->approve($approval, $request->comment);
            
            return response()->json([
                'message' => 'Approval submitted successfully',
                'approval' => $approval->fresh(),
            ]);
        } catch (\Exception $e) {
            return response()->json([
                'message' => 'Failed to submit approval',
                'error' => $e->getMessage(),
            ], 400);
        }
    }
    
    public function reject(Request $request, Approval $approval)
    {
        $request->validate([
            'comment' => 'required|string',
        ]);
        
        if (!$this->approvalEngine->canUserApprove($approval, auth('tenant')->id())) {
            return response()->json(['message' => 'Unauthorized or approval not pending'], 403);
        }
        
        try {
            $this->approvalEngine->reject($approval, $request->comment);
            
            return response()->json([
                'message' => 'Submission rejected successfully',
                'approval' => $approval->fresh(),
            ]);
        } catch (\Exception $e) {
            return response()->json([
                'message' => 'Failed to reject submission',
                'error' => $e->getMessage(),
            ], 400);
        }
    }
    
    public function getProgress(FormSubmission $submission)
    {
        $progress = $this->approvalEngine->getApprovalProgress($submission);
        
        return response()->json([
            'submission' => $submission,
            'approval_progress' => $progress,
        ]);
    }
}

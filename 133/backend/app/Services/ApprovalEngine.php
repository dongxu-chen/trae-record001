<?php

namespace App\Services;

use App\Models\FormSubmission;
use App\Models\Approval;
use App\Models\ApprovalStep;
use App\Models\ApprovalFlow;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class ApprovalEngine
{
    public function initializeApprovals(FormSubmission $submission, ApprovalFlow $flow)
    {
        $steps = $flow->steps()->orderBy('order', 'asc')->get();
        
        foreach ($steps as $step) {
            $approvers = $step->approvers;
            
            if ($approvers->isEmpty()) {
                Log::warning("No approvers found for step: {$step->id}");
                continue;
            }
            
            foreach ($approvers as $approver) {
                Approval::create([
                    'submission_id' => $submission->id,
                    'step_id' => $step->id,
                    'approver_id' => $approver->id,
                    'step_order' => $step->order,
                    'status' => $step->order == 1 ? Approval::STATUS_PENDING : Approval::STATUS_WAITING,
                ]);
            }
        }
    }
    
    public function approve(Approval $approval, ?string $comment = null)
    {
        if (!$approval->isPending()) {
            throw new \Exception("This approval is not pending.");
        }
        
        DB::connection('tenant')->beginTransaction();
        
        try {
            $approval->update([
                'status' => Approval::STATUS_APPROVED,
                'comment' => $comment,
                'approved_at' => now(),
            ]);
            
            $step = $approval->step;
            $submission = $approval->submission;
            
            if (!$step) {
                throw new \Exception("Approval step not found.");
            }
            
            $stepResult = $this->evaluateStepResult($step, $submission);
            
            if ($stepResult === 'rejected') {
                $this->rejectRemainingApprovals($submission, $approval->step_order);
                $submission->update(['status' => 'rejected']);
            } elseif ($stepResult === 'approved') {
                $nextStepApproved = $this->activateNextStep($submission, $approval->step_order);
                if (!$nextStepApproved) {
                    $submission->update(['status' => 'approved']);
                }
            }
            
            DB::connection('tenant')->commit();
            
            return true;
        } catch (\Exception $e) {
            DB::connection('tenant')->rollBack();
            Log::error("Approval failed: {$e->getMessage()}", [
                'approval_id' => $approval->id,
                'exception' => $e,
            ]);
            throw $e;
        }
    }
    
    public function reject(Approval $approval, string $comment)
    {
        if (!$approval->isPending()) {
            throw new \Exception("This approval is not pending.");
        }
        
        DB::connection('tenant')->beginTransaction();
        
        try {
            $approval->update([
                'status' => Approval::STATUS_REJECTED,
                'comment' => $comment,
                'approved_at' => now(),
            ]);
            
            $submission = $approval->submission;
            
            $this->rejectRemainingApprovals($submission, $approval->step_order);
            $submission->update(['status' => 'rejected']);
            
            DB::connection('tenant')->commit();
            
            return true;
        } catch (\Exception $e) {
            DB::connection('tenant')->rollBack();
            Log::error("Rejection failed: {$e->getMessage()}", [
                'approval_id' => $approval->id,
                'exception' => $e,
            ]);
            throw $e;
        }
    }
    
    protected function evaluateStepResult(ApprovalStep $step, FormSubmission $submission)
    {
        $stepApprovals = Approval::forStep($step->id)
            ->where('submission_id', $submission->id)
            ->get();
        
        $totalApprovers = $stepApprovals->count();
        $approvedCount = $stepApprovals->where('status', Approval::STATUS_APPROVED)->count();
        $rejectedCount = $stepApprovals->where('status', Approval::STATUS_REJECTED)->count();
        
        Log::debug("Evaluating approval step", [
            'step_id' => $step->id,
            'approval_mode' => $step->approval_mode,
            'total' => $totalApprovers,
            'approved' => $approvedCount,
            'rejected' => $rejectedCount,
        ]);
        
        if ($rejectedCount > 0) {
            return 'rejected';
        }
        
        switch ($step->approval_mode) {
            case ApprovalStep::APPROVAL_MODE_ANY:
                return $approvedCount >= 1 ? 'approved' : 'pending';
                
            case ApprovalStep::APPROVAL_MODE_ALL:
                return $approvedCount === $totalApprovers ? 'approved' : 'pending';
                
            case ApprovalStep::APPROVAL_MODE_THRESHOLD:
                $threshold = $step->approve_threshold ?: 1;
                return $approvedCount >= $threshold ? 'approved' : 'pending';
                
            default:
                return $approvedCount === $totalApprovers ? 'approved' : 'pending';
        }
    }
    
    protected function activateNextStep(FormSubmission $submission, int $currentOrder)
    {
        $nextStepApprovals = Approval::where('submission_id', $submission->id)
            ->where('step_order', $currentOrder + 1)
            ->get();
        
        if ($nextStepApprovals->isEmpty()) {
            return false;
        }
        
        $nextStepApprovals->each(function ($approval) {
            $approval->update(['status' => Approval::STATUS_PENDING]);
        });
        
        return true;
    }
    
    protected function rejectRemainingApprovals(FormSubmission $submission, int $currentOrder)
    {
        Approval::where('submission_id', $submission->id)
            ->where('step_order', '>=', $currentOrder)
            ->where('status', Approval::STATUS_PENDING)
            ->update([
                'status' => Approval::STATUS_CANCELLED,
                'comment' => 'Cancelled due to rejection',
            ]);
        
        Approval::where('submission_id', $submission->id)
            ->where('step_order', '>', $currentOrder)
            ->where('status', Approval::STATUS_WAITING)
            ->update([
                'status' => Approval::STATUS_CANCELLED,
                'comment' => 'Cancelled due to rejection',
            ]);
    }
    
    public function getApprovalProgress(FormSubmission $submission)
    {
        $approvals = Approval::where('submission_id', $submission->id)
            ->with('approver', 'step')
            ->orderBy('step_order', 'asc')
            ->get();
        
        $steps = [];
        
        foreach ($approvals->groupBy('step_order') as $order => $stepApprovals) {
            $total = $stepApprovals->count();
            $approved = $stepApprovals->where('status', Approval::STATUS_APPROVED)->count();
            $rejected = $stepApprovals->where('status', Approval::STATUS_REJECTED)->count();
            $pending = $stepApprovals->where('status', Approval::STATUS_PENDING)->count();
            
            $step = $stepApprovals->first()->step;
            
            $steps[] = [
                'order' => $order,
                'name' => $step?->name ?? "Step {$order}",
                'total' => $total,
                'approved' => $approved,
                'rejected' => $rejected,
                'pending' => $pending,
                'mode' => $step?->approval_mode ?? 'all',
                'threshold' => $step?->approve_threshold ?? null,
                'approvals' => $stepApprovals,
            ];
        }
        
        return $steps;
    }
    
    public function canUserApprove(Approval $approval, int $userId): bool
    {
        return $approval->approver_id === $userId 
            && $approval->status === Approval::STATUS_PENDING;
    }
}

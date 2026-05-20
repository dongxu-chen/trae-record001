<?php

namespace App\Http\Controllers\Api;

use App\Models\Tenant;
use App\Services\TenantUsageService;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;

class TenantUsageController extends Controller
{
    protected $usageService;
    
    public function __construct(TenantUsageService $usageService)
    {
        $this->middleware('auth:sanctum');
        $this->usageService = $usageService;
    }

    public function dashboard(Tenant $tenant)
    {
        $stats = $this->usageService->getDashboardStats($tenant);
        
        return response()->json([
            'tenant' => $tenant->only(['id', 'name', 'domain', 'plan']),
            'stats' => $stats,
        ]);
    }

    public function currentUsage(Request $request, Tenant $tenant)
    {
        $periodType = $request->query('period_type', 'monthly');
        $usage = $this->usageService->getCurrentUsage($tenant, $periodType);
        
        return response()->json([
            'tenant' => $tenant->only(['id', 'name']),
            'usage' => $usage,
        ]);
    }

    public function history(Request $request, Tenant $tenant)
    {
        $request->validate([
            'period_type' => 'nullable|in:daily,weekly,monthly',
            'limit' => 'nullable|integer|min:1|max:365',
        ]);
        
        $periodType = $request->query('period_type', 'daily');
        $limit = $request->query('limit', 30);
        
        $history = $this->usageService->getUsageHistory($tenant, $periodType, $limit);
        
        return response()->json([
            'tenant' => $tenant->only(['id', 'name']),
            'period_type' => $periodType,
            'history' => $history,
        ]);
    }

    public function recordUsage(Tenant $tenant)
    {
        $usage = $this->usageService->recordUsage($tenant);
        
        return response()->json([
            'message' => 'Usage recorded successfully',
            'usage' => $usage,
        ]);
    }

    public function recordAllTenantsUsage(Request $request)
    {
        $request->validate([
            'period_type' => 'nullable|in:daily,weekly,monthly',
        ]);
        
        $results = $this->usageService->recordAllTenantsUsage($request->query('period_type'));
        
        $successCount = collect($results)->where('success', true)->count();
        $failedCount = count($results) - $successCount;
        
        return response()->json([
            'message' => "Usage recording completed. Success: {$successCount}, Failed: {$failedCount}",
            'results' => $results,
        ]);
    }

    public function exportUsage(Request $request, Tenant $tenant)
    {
        $request->validate([
            'period_type' => 'nullable|in:daily,weekly,monthly',
            'start_date' => 'nullable|date',
            'end_date' => 'nullable|date',
            'format' => 'nullable|in:json,csv',
        ]);
        
        $periodType = $request->query('period_type', 'monthly');
        $format = $request->query('format', 'json');
        
        $history = $this->usageService->getUsageHistory($tenant, $periodType, 365);
        
        if ($format === 'csv') {
            $headers = [
                'Content-Type' => 'text/csv',
                'Content-Disposition' => "attachment; filename=\"{$tenant->name}-usage-export.csv\"",
            ];
            
            $callback = function () use ($history) {
                $file = fopen('php://output', 'w');
                
                fputcsv($file, [
                    'Period Start',
                    'Period End',
                    'Forms Count',
                    'Submissions Count',
                    'Users Count',
                    'Storage Used',
                    'API Calls',
                    'Webhook Calls',
                ]);
                
                foreach ($history as $log) {
                    fputcsv($file, [
                        $log->period_start->toDateString(),
                        $log->period_end->toDateString(),
                        $log->forms_count,
                        $log->submissions_count,
                        $log->users_count,
                        $log->storage_used,
                        $log->api_calls_count,
                        $log->webhook_calls_count,
                    ]);
                }
                
                fclose($file);
            };
            
            return response()->stream($callback, 200, $headers);
        }
        
        return response()->json([
            'tenant' => $tenant->only(['id', 'name']),
            'period_type' => $periodType,
            'usage_history' => $history,
        ]);
    }
}

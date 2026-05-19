<?php

namespace App\Services;

use App\Models\Tenant;
use App\Models\TenantUsageLog;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class TenantUsageService
{
    public function recordUsage(Tenant $tenant, string $periodType = null): TenantUsageLog
    {
        $periodType = $periodType ?? TenantUsageLog::PERIOD_DAILY;
        
        $dates = $this->getPeriodDates($periodType);
        
        $existingLog = TenantUsageLog::where('tenant_id', $tenant->id)
            ->where('period_type', $periodType)
            ->where('period_start', $dates['start'])
            ->where('period_end', $dates['end'])
            ->first();
        
        if ($existingLog) {
            return $this->updateUsageLog($existingLog, $tenant);
        }
        
        return $this->createUsageLog($tenant, $periodType, $dates);
    }
    
    protected function createUsageLog(Tenant $tenant, string $periodType, array $dates): TenantUsageLog
    {
        $usageData = $this->collectTenantUsage($tenant);
        
        return TenantUsageLog::create(array_merge([
            'tenant_id' => $tenant->id,
            'period_type' => $periodType,
            'period_start' => $dates['start'],
            'period_end' => $dates['end'],
        ], $usageData));
    }
    
    protected function updateUsageLog(TenantUsageLog $log, Tenant $tenant): TenantUsageLog
    {
        $usageData = $this->collectTenantUsage($tenant);
        $log->update($usageData);
        
        return $log->fresh();
    }
    
    protected function collectTenantUsage(Tenant $tenant): array
    {
        $tenant->configure();
        
        $formsCount = DB::connection('tenant')->table('forms')->count();
        $submissionsCount = DB::connection('tenant')->table('form_submissions')->count();
        $usersCount = DB::connection('tenant')->table('tenant_users')->count();
        
        $webhookCallsCount = DB::connection('tenant')->table('webhook_deliveries')
            ->where('status', 'success')
            ->count();
        
        $storageUsed = 0;
        
        return [
            'forms_count' => $formsCount,
            'submissions_count' => $submissionsCount,
            'users_count' => $usersCount,
            'storage_used' => $storageUsed,
            'api_calls_count' => 0,
            'webhook_calls_count' => $webhookCallsCount,
        ];
    }
    
    protected function getPeriodDates(string $periodType): array
    {
        $now = now();
        
        switch ($periodType) {
            case TenantUsageLog::PERIOD_DAILY:
                $start = $now->copy()->startOfDay();
                $end = $now->copy()->endOfDay();
                break;
            case TenantUsageLog::PERIOD_WEEKLY:
                $start = $now->copy()->startOfWeek();
                $end = $now->copy()->endOfWeek();
                break;
            case TenantUsageLog::PERIOD_MONTHLY:
                $start = $now->copy()->startOfMonth();
                $end = $now->copy()->endOfMonth();
                break;
            default:
                $start = $now->copy()->startOfDay();
                $end = $now->copy()->endOfDay();
        }
        
        return ['start' => $start, 'end' => $end];
    }
    
    public function getCurrentUsage(Tenant $tenant, string $periodType = null): ?TenantUsageLog
    {
        $periodType = $periodType ?? TenantUsageLog::PERIOD_MONTHLY;
        $dates = $this->getPeriodDates($periodType);
        
        $log = TenantUsageLog::where('tenant_id', $tenant->id)
            ->where('period_type', $periodType)
            ->where('period_start', $dates['start'])
            ->where('period_end', $dates['end'])
            ->first();
        
        if (!$log) {
            $log = $this->recordUsage($tenant, $periodType);
        }
        
        return $log;
    }
    
    public function getUsageHistory(Tenant $tenant, string $periodType, int $limit = 30)
    {
        return TenantUsageLog::forTenant($tenant->id)
            ->byPeriodType($periodType)
            ->orderBy('period_end', 'desc')
            ->limit($limit)
            ->get();
    }
    
    public function getDashboardStats(Tenant $tenant): array
    {
        $monthlyUsage = $this->getCurrentUsage($tenant, TenantUsageLog::PERIOD_MONTHLY);
        $dailyUsage = $this->getCurrentUsage($tenant, TenantUsageLog::PERIOD_DAILY);
        $weeklyLogs = $this->getUsageHistory($tenant, TenantUsageLog::PERIOD_DAILY, 7);
        
        return [
            'current_month' => $monthlyUsage,
            'today' => $dailyUsage,
            'weekly_trend' => $weeklyLogs->reverse()->values(),
            'summary' => [
                'total_forms' => $monthlyUsage->forms_count ?? 0,
                'total_submissions' => $monthlyUsage->submissions_count ?? 0,
                'total_users' => $monthlyUsage->users_count ?? 0,
                'webhook_calls' => $monthlyUsage->webhook_calls_count ?? 0,
            ],
        ];
    }
    
    public function recordAllTenantsUsage(string $periodType = null): array
    {
        $periodType = $periodType ?? TenantUsageLog::PERIOD_DAILY;
        $tenants = Tenant::where('is_active', true)->get();
        $results = [];
        
        foreach ($tenants as $tenant) {
            try {
                $log = $this->recordUsage($tenant, $periodType);
                $results[$tenant->id] = [
                    'success' => true,
                    'tenant' => $tenant->name,
                    'log_id' => $log->id,
                ];
            } catch (\Exception $e) {
                Log::error("Failed to record usage for tenant {$tenant->id}: {$e->getMessage()}");
                $results[$tenant->id] = [
                    'success' => false,
                    'tenant' => $tenant->name,
                    'error' => $e->getMessage(),
                ];
            }
        }
        
        return $results;
    }
}

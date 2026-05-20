<?php

namespace App\Http\Middleware;

use Closure;
use App\Models\Tenant;
use App\Services\DatabaseConnectionPool;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;

class TenantConnectionPoolMiddleware
{
    protected $connectionPool;
    
    public function __construct(DatabaseConnectionPool $connectionPool)
    {
        $this->connectionPool = $connectionPool;
    }
    
    public function handle(Request $request, Closure $next)
    {
        $domain = $request->getHost();
        $tenant = Tenant::where('domain', $domain)
            ->orWhere('domain', explode('.', $domain)[0])
            ->first();
        
        if (!$tenant) {
            return response()->json(['message' => 'Tenant not found.'], 404);
        }
        
        if (!$tenant->is_active) {
            return response()->json(['message' => 'Tenant is inactive.'], 403);
        }
        
        try {
            $connection = $this->connectionPool->getConnection($tenant->database);
            
            app()->instance('db.tenant', $connection);
            
            $request->merge(['tenant' => $tenant]);
            $request->merge(['tenant_database' => $tenant->database]);
            
        } catch (\Exception $e) {
            Log::error('Failed to get tenant database connection', [
                'tenant' => $tenant->id,
                'database' => $tenant->database,
                'error' => $e->getMessage(),
            ]);
            return response()->json(['message' => 'Database connection error.'], 500);
        }
        
        $response = $next($request);
        
        register_shutdown_function(function () use ($tenant) {
            $this->connectionPool->releaseConnection($tenant->database);
        });
        
        return $response;
    }
    
    public function terminate(Request $request, $response)
    {
        if ($request->has('tenant_database')) {
            $this->connectionPool->releaseConnection($request->input('tenant_database'));
        }
        
        if (mt_rand(1, 100) <= 5) {
            $this->connectionPool->cleanupAllExpired();
            $leaks = $this->connectionPool->detectLeaks();
            
            if (!empty($leaks)) {
                Log::warning('Connection pool monitoring detected potential issues', [
                    'stats' => $this->connectionPool->getConnectionStats(),
                    'leaks' => $leaks,
                ]);
            }
        }
    }
}

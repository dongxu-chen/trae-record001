<?php

namespace App\Http\Middleware;

use Closure;
use App\Models\Tenant;
use Illuminate\Http\Request;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

class TenantMiddleware
{
    public function handle(Request $request, Closure $next)
    {
        $domain = $request->getHost();
        
        $tenant = Tenant::where('domain', $domain)
            ->orWhere('domain', explode('.', $domain)[0])
            ->first();

        if (!$tenant) {
            throw new NotFoundHttpException('Tenant not found.');
        }

        if (!$tenant->is_active) {
            return response()->json(['message' => 'Tenant is inactive.'], 403);
        }

        $tenant->configure();
        
        $request->merge(['tenant' => $tenant]);

        return $next($request);
    }
}

<?php

namespace App\Http\Controllers\Api;

use App\Models\Tenant;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class TenantController extends Controller
{
    public function index()
    {
        $tenants = Tenant::paginate(10);
        return response()->json($tenants);
    }

    public function store(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'domain' => 'required|string|unique:tenants',
            'email' => 'required|email',
        ]);

        $database = 'saas_tenant_' . Str::random(10);

        $tenant = Tenant::create([
            'name' => $request->name,
            'domain' => $request->domain,
            'database' => $database,
            'email' => $request->email,
            'is_active' => true,
        ]);

        $tenant->createDatabase();

        return response()->json([
            'message' => 'Tenant created successfully',
            'tenant' => $tenant,
        ], 201);
    }

    public function show(Tenant $tenant)
    {
        return response()->json($tenant);
    }

    public function update(Request $request, Tenant $tenant)
    {
        $request->validate([
            'name' => 'sometimes|string|max:255',
            'domain' => 'sometimes|string|unique:tenants,domain,' . $tenant->id,
            'email' => 'sometimes|email',
            'is_active' => 'sometimes|boolean',
        ]);

        $tenant->update($request->all());

        return response()->json([
            'message' => 'Tenant updated successfully',
            'tenant' => $tenant,
        ]);
    }

    public function destroy(Tenant $tenant)
    {
        $tenant->delete();
        return response()->json([
            'message' => 'Tenant deleted successfully',
        ]);
    }
}

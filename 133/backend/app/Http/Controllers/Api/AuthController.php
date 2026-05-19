<?php

namespace App\Http\Controllers\Api;

use App\Models\TenantUser;
use Illuminate\Http\Request;
use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    public function register(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|string|email|unique:tenant_users',
            'password' => 'required|string|min:6|confirmed',
            'role' => 'sometimes|string',
        ]);

        $user = TenantUser::create([
            'name' => $request->name,
            'email' => $request->email,
            'password' => Hash::make($request->password),
            'role' => $request->role ?? 'user',
            'is_active' => true,
        ]);

        $token = auth('tenant')->login($user);

        return response()->json([
            'message' => 'User registered successfully',
            'user' => $user,
            'token' => $token,
        ], 201);
    }

    public function login(Request $request)
    {
        $request->validate([
            'email' => 'required|email',
            'password' => 'required|string',
        ]);

        $credentials = $request->only('email', 'password');

        if (!$token = auth('tenant')->attempt($credentials)) {
            throw ValidationException::withMessages([
                'email' => ['The provided credentials are incorrect.'],
            ]);
        }

        $user = auth('tenant')->user();

        if (!$user->is_active) {
            return response()->json(['message' => 'Account is inactive.'], 403);
        }

        return response()->json([
            'message' => 'Login successful',
            'user' => $user,
            'token' => $token,
        ]);
    }

    public function logout()
    {
        auth('tenant')->logout();
        return response()->json(['message' => 'Successfully logged out']);
    }

    public function me()
    {
        return response()->json(auth('tenant')->user());
    }

    public function refresh()
    {
        return response()->json([
            'token' => auth('tenant')->refresh(),
        ]);
    }
}

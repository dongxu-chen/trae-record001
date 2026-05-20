<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\TenantController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\FormController;
use App\Http\Controllers\Api\FormSubmissionController;
use App\Http\Controllers\Api\ApprovalController;
use App\Http\Controllers\Api\PdfTemplateController;
use App\Http\Controllers\Api\WebhookController;
use App\Http\Controllers\Api\TenantUsageController;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

Route::prefix('admin')->group(function () {
    Route::apiResource('tenants', TenantController::class);
    
    Route::prefix('tenants/{tenant}')->group(function () {
        Route::get('usage/dashboard', [TenantUsageController::class, 'dashboard']);
        Route::get('usage/current', [TenantUsageController::class, 'currentUsage']);
        Route::get('usage/history', [TenantUsageController::class, 'history']);
        Route::post('usage/record', [TenantUsageController::class, 'recordUsage']);
        Route::get('usage/export', [TenantUsageController::class, 'exportUsage']);
    });
    
    Route::post('usage/record-all', [TenantUsageController::class, 'recordAllTenantsUsage']);
});

Route::middleware(['tenant'])->group(function () {
    Route::post('register', [AuthController::class, 'register']);
    Route::post('login', [AuthController::class, 'login']);
    
    Route::middleware('auth:tenant')->group(function () {
        Route::post('logout', [AuthController::class, 'logout']);
        Route::get('me', [AuthController::class, 'me']);
        Route::post('refresh', [AuthController::class, 'refresh']);
        
        Route::apiResource('forms', FormController::class);
        Route::post('forms/{form}/publish', [FormController::class, 'publish']);
        
        Route::prefix('forms/{form}')->group(function () {
            Route::get('versions', [FormController::class, 'versions']);
            Route::get('versions/{version}', [FormController::class, 'showVersion']);
            Route::post('versions/{version}/rollback', [FormController::class, 'rollback']);
            Route::post('versions/compare', [FormController::class, 'compareVersions']);
        });
        
        Route::get('submissions', [FormSubmissionController::class, 'index']);
        Route::post('forms/{form}/submit', [FormSubmissionController::class, 'store']);
        Route::get('submissions/{submission}', [FormSubmissionController::class, 'show']);
        Route::post('submissions/export', [FormSubmissionController::class, 'export']);
        Route::get('submissions/export/stats', [FormSubmissionController::class, 'exportStats']);
        
        Route::get('approval-flows', [ApprovalController::class, 'flows']);
        Route::post('approval-flows', [ApprovalController::class, 'storeFlow']);
        Route::get('approval-flows/{flow}', [ApprovalController::class, 'showFlow']);
        Route::put('approval-flows/{flow}', [ApprovalController::class, 'updateFlow']);
        Route::delete('approval-flows/{flow}', [ApprovalController::class, 'deleteFlow']);
        
        Route::get('my-approvals', [ApprovalController::class, 'myApprovals']);
        Route::post('approvals/{approval}/approve', [ApprovalController::class, 'approve']);
        Route::post('approvals/{approval}/reject', [ApprovalController::class, 'reject']);
        Route::get('submissions/{submission}/approval-progress', [ApprovalController::class, 'getProgress']);
        
        Route::apiResource('pdf-templates', PdfTemplateController::class);
        Route::prefix('pdf-templates')->group(function () {
            Route::get('default/{form}', [PdfTemplateController::class, 'getDefaultTemplate']);
            Route::post('{template}/preview', [PdfTemplateController::class, 'preview']);
            Route::post('{template}/generate', [PdfTemplateController::class, 'generatePdf']);
        });
        
        Route::get('print-jobs', [PdfTemplateController::class, 'printJobs']);
        Route::get('print-jobs/{printJob}/download', [PdfTemplateController::class, 'downloadPdf']);
        
        Route::apiResource('webhook-endpoints', WebhookController::class);
        Route::prefix('webhook-endpoints')->group(function () {
            Route::post('{endpoint}/regenerate-secret', [WebhookController::class, 'regenerateSecret']);
            Route::post('{endpoint}/test', [WebhookController::class, 'testEndpoint']);
        });
        
        Route::get('webhook-deliveries', [WebhookController::class, 'deliveries']);
        Route::get('webhook-deliveries/{delivery}', [WebhookController::class, 'showDelivery']);
        Route::post('webhook-deliveries/{delivery}/redeliver', [WebhookController::class, 'redeliver']);
        
        Route::get('webhook-events', [WebhookController::class, 'getAvailableEvents']);
        Route::get('webhook-stats', [WebhookController::class, 'getStats']);
    });
});

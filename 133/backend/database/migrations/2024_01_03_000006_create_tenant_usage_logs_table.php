<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('tenant_usage_logs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('tenant_id')->constrained()->onDelete('cascade');
            $table->string('period_type');
            $table->timestamp('period_start');
            $table->timestamp('period_end');
            $table->integer('forms_count')->default(0);
            $table->integer('submissions_count')->default(0);
            $table->integer('users_count')->default(0);
            $table->bigInteger('storage_used')->default(0);
            $table->integer('api_calls_count')->default(0);
            $table->integer('webhook_calls_count')->default(0);
            $table->timestamps();
            
            $table->unique(['tenant_id', 'period_type', 'period_start', 'period_end'], 'tenant_usage_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('tenant_usage_logs');
    }
};

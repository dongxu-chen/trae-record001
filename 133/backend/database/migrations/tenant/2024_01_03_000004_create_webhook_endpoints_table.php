<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('webhook_endpoints', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->text('description')->nullable();
            $table->string('url');
            $table->string('method')->default('POST');
            $table->json('headers')->nullable();
            $table->json('events')->nullable();
            $table->boolean('is_active')->default(true);
            $table->string('secret_key');
            $table->integer('retry_count')->default(3);
            $table->integer('retry_delay')->default(60);
            $table->integer('timeout')->default(30);
            $table->foreignId('created_by')->constrained('tenant_users')->onDelete('cascade');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('webhook_endpoints');
    }
};

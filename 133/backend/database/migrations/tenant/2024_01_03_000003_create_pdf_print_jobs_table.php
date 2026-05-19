<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('pdf_print_jobs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('template_id')->constrained('pdf_templates')->onDelete('cascade');
            $table->foreignId('submission_id')->constrained('form_submissions')->onDelete('cascade');
            $table->foreignId('created_by')->constrained('tenant_users')->onDelete('cascade');
            $table->string('status')->default('pending');
            $table->string('file_path')->nullable();
            $table->bigInteger('file_size')->nullable();
            $table->integer('page_count')->nullable();
            $table->text('error_message')->nullable();
            $table->timestamp('printed_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('pdf_print_jobs');
    }
};

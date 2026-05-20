<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('form_versions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('form_id')->constrained()->onDelete('cascade');
            $table->integer('version_number');
            $table->string('name');
            $table->text('description')->nullable();
            $table->json('schema')->nullable();
            $table->json('fields')->nullable();
            $table->foreignId('created_by')->constrained('tenant_users')->onDelete('cascade');
            $table->boolean('is_current')->default(false);
            $table->text('change_note')->nullable();
            $table->timestamps();
            
            $table->unique(['form_id', 'version_number']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('form_versions');
    }
};

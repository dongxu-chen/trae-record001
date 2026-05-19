<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('approval_steps', function (Blueprint $table) {
            $table->id();
            $table->foreignId('approval_flow_id')->constrained()->onDelete('cascade');
            $table->string('name');
            $table->integer('order');
            $table->foreignId('approver_id')->nullable()->constrained('tenant_users')->onDelete('set null');
            $table->string('approver_role')->nullable();
            $table->string('approval_type')->default('person');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('approval_steps');
    }
};

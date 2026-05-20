<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('approval_steps', function (Blueprint $table) {
            if (!Schema::hasColumn('approval_steps', 'approval_mode')) {
                $table->string('approval_mode')->default('all');
            }
            if (!Schema::hasColumn('approval_steps', 'approve_threshold')) {
                $table->integer('approve_threshold')->nullable();
            }
            if (!Schema::hasColumn('approval_steps', 'approver_ids')) {
                $table->json('approver_ids')->nullable();
            }
        });
    }

    public function down(): void
    {
        Schema::table('approval_steps', function (Blueprint $table) {
            $table->dropColumn(['approval_mode', 'approve_threshold', 'approver_ids']);
        });
    }
};

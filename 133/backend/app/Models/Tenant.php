<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

class Tenant extends Model
{
    protected $fillable = [
        'name',
        'domain',
        'database',
        'email',
        'is_active',
        'expires_at',
    ];

    protected $casts = [
        'is_active' => 'boolean',
        'expires_at' => 'datetime',
    ];

    public function configure()
    {
        config([
            'database.connections.tenant.database' => $this->database,
        ]);

        DB::purge('tenant');
        DB::reconnect('tenant');
    }

    public function createDatabase()
    {
        $databaseName = $this->database;
        
        DB::statement("CREATE DATABASE IF NOT EXISTS `{$databaseName}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
        
        $this->configure();
        
        $this->runMigrations();
    }

    protected function runMigrations()
    {
        $migrationPath = database_path('migrations/tenant');
        
        if (is_dir($migrationPath)) {
            $migrations = glob($migrationPath . '/*.php');
            
            foreach ($migrations as $migration) {
                require_once $migration;
                
                $className = $this->getMigrationClassName($migration);
                
                if (class_exists($className)) {
                    $migrationInstance = new $className();
                    $migrationInstance->up();
                }
            }
        }
    }

    protected function getMigrationClassName($filePath)
    {
        $fileName = basename($filePath, '.php');
        $parts = explode('_', $fileName);
        $parts = array_slice($parts, 4);
        $className = '';
        
        foreach ($parts as $part) {
            $className .= ucfirst($part);
        }
        
        return $className;
    }

    public function users()
    {
        return $this->hasMany(TenantUser::class);
    }
}

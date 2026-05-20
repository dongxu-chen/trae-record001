<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use WeakMap;

class DatabaseConnectionPool
{
    protected static $instance = null;
    
    protected $connections = [];
    
    protected $connectionUsage = [];
    
    protected $maxConnectionsPerTenant = 5;
    
    protected $leaseExpiry = 300;
    
    protected $monitoringEnabled = true;
    
    protected function __construct() {}
    
    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    public function getConnection(string $tenantDatabase)
    {
        $connectionKey = "tenant:{$tenantDatabase}";
        
        if (isset($this->connections[$connectionKey])) {
            $connection = $this->connections[$connectionKey]['connection'];
            
            try {
                $connection->getPdo();
                $this->markConnectionUsed($connectionKey);
                return $connection;
            } catch (\Exception $e) {
                $this->purgeConnection($connectionKey);
            }
        }
        
        if ($this->getTenantConnectionCount($tenantDatabase) >= $this->maxConnectionsPerTenant) {
            $this->cleanupExpiredConnections($tenantDatabase);
        }
        
        return $this->createConnection($tenantDatabase, $connectionKey);
    }
    
    protected function createConnection(string $tenantDatabase, string $connectionKey)
    {
        $config = config("database.connections.tenant");
        $config['database'] = $tenantDatabase;
        
        config(["database.connections.{$connectionKey}" => $config]);
        
        $connection = DB::connection($connectionKey);
        $connection->setDatabaseName($tenantDatabase);
        
        try {
            $connection->getPdo();
        } catch (\Exception $e) {
            Log::error("Failed to create tenant database connection: {$e->getMessage()}", [
                'database' => $tenantDatabase,
            ]);
            throw $e;
        }
        
        $this->connections[$connectionKey] = [
            'connection' => $connection,
            'created_at' => time(),
            'last_used_at' => time(),
            'tenant' => $tenantDatabase,
            'lease_count' => 0,
        ];
        
        Log::debug("Created new tenant database connection: {$connectionKey}");
        
        return $connection;
    }
    
    public function releaseConnection(string $tenantDatabase)
    {
        $connectionKey = "tenant:{$tenantDatabase}";
        
        if (isset($this->connections[$connectionKey])) {
            $this->connections[$connectionKey]['lease_count']--;
            
            if ($this->connections[$connectionKey]['lease_count'] <= 0) {
                $this->connections[$connectionKey]['lease_count'] = 0;
                Log::debug("Connection returned to pool: {$connectionKey}");
            }
        }
    }
    
    public function purgeConnection(string $connectionKey)
    {
        if (isset($this->connections[$connectionKey])) {
            try {
                $this->connections[$connectionKey]['connection']->disconnect();
            } catch (\Exception $e) {
                Log::warning("Error disconnecting database: {$e->getMessage()}");
            }
            
            unset($this->connections[$connectionKey]);
            Log::debug("Purged connection: {$connectionKey}");
        }
    }
    
    protected function markConnectionUsed(string $connectionKey)
    {
        if (isset($this->connections[$connectionKey])) {
            $this->connections[$connectionKey]['last_used_at'] = time();
            $this->connections[$connectionKey]['lease_count']++;
        }
    }
    
    protected function getTenantConnectionCount(string $tenantDatabase): int
    {
        return count(array_filter($this->connections, function ($conn) use ($tenantDatabase) {
            return $conn['tenant'] === $tenantDatabase;
        }));
    }
    
    protected function cleanupExpiredConnections(string $tenantDatabase)
    {
        $now = time();
        
        foreach ($this->connections as $key => $conn) {
            if ($conn['tenant'] === $tenantDatabase 
                && ($now - $conn['last_used_at']) > $this->leaseExpiry) {
                $this->purgeConnection($key);
            }
        }
    }
    
    public function cleanupAllExpired()
    {
        $now = time();
        $purgedCount = 0;
        
        foreach ($this->connections as $key => $conn) {
            if (($now - $conn['last_used_at']) > $this->leaseExpiry) {
                $this->purgeConnection($key);
                $purgedCount++;
            }
        }
        
        if ($purgedCount > 0) {
            Log::debug("Purged {$purgedCount} expired connections");
        }
    }
    
    public function getConnectionStats(): array
    {
        $totalConnections = count($this->connections);
        $tenantStats = [];
        
        foreach ($this->connections as $key => $conn) {
            $tenant = $conn['tenant'];
            if (!isset($tenantStats[$tenant])) {
                $tenantStats[$tenant] = 0;
            }
            $tenantStats[$tenant]++;
        }
        
        return [
            'total_connections' => $totalConnections,
            'tenant_distribution' => $tenantStats,
            'max_per_tenant' => $this->maxConnectionsPerTenant,
            'lease_expiry' => $this->leaseExpiry,
        ];
    }
    
    public function detectLeaks(): array
    {
        $leaks = [];
        $now = time();
        
        foreach ($this->connections as $key => $conn) {
            $idleTime = $now - $conn['last_used_at'];
            $leaseCount = $conn['lease_count'];
            
            if ($idleTime > 60 && $leaseCount > 10) {
                $leaks[] = [
                    'connection' => $key,
                    'idle_time' => $idleTime,
                    'lease_count' => $leaseCount,
                    'warning' => 'Potential connection leak detected',
                ];
            }
        }
        
        if (!empty($leaks)) {
            Log::warning('Database connection leaks detected', ['leaks' => $leaks]);
        }
        
        return $leaks;
    }
    
    public function setMaxConnections(int $max): void
    {
        $this->maxConnectionsPerTenant = $max;
    }
    
    public function setLeaseExpiry(int $seconds): void
    {
        $this->leaseExpiry = $seconds;
    }
    
    public function __destruct()
    {
        foreach (array_keys($this->connections) as $key) {
            $this->purgeConnection($key);
        }
    }
}

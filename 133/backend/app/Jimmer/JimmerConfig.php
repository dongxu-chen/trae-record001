<?php

namespace App\Jimmer;

class JimmerConfig
{
    protected $connectionName = 'tenant';
    protected $tablePrefix = '';
    protected $enableEncryption = true;
    protected $encryptionKey;
    protected $enableOptimization = true;
    protected $maxBatchSize = 100;
    protected $enableCache = true;
    protected $cacheTTL = 3600;
    
    protected $entityPaths = [];
    protected $migrationPath;
    
    protected $listeners = [];
    
    public function __construct()
    {
        $this->encryptionKey = env('JIMMER_ENCRYPTION_KEY', env('APP_KEY'));
        $this->migrationPath = database_path('jimmer');
    }
    
    public function setConnectionName(string $name): self
    {
        $this->connectionName = $name;
        return $this;
    }
    
    public function getConnectionName(): string
    {
        return $this->connectionName;
    }
    
    public function setTablePrefix(string $prefix): self
    {
        $this->tablePrefix = $prefix;
        return $this;
    }
    
    public function getTablePrefix(): string
    {
        return $this->tablePrefix;
    }
    
    public function enableEncryption(bool $enable = true): self
    {
        $this->enableEncryption = $enable;
        return $this;
    }
    
    public function isEncryptionEnabled(): bool
    {
        return $this->enableEncryption;
    }
    
    public function setEncryptionKey(string $key): self
    {
        $this->encryptionKey = $key;
        return $this;
    }
    
    public function getEncryptionKey(): ?string
    {
        return $this->encryptionKey;
    }
    
    public function enableOptimization(bool $enable = true): self
    {
        $this->enableOptimization = $enable;
        return $this;
    }
    
    public function isOptimizationEnabled(): bool
    {
        return $this->enableOptimization;
    }
    
    public function setMaxBatchSize(int $size): self
    {
        $this->maxBatchSize = $size;
        return $this;
    }
    
    public function getMaxBatchSize(): int
    {
        return $this->maxBatchSize;
    }
    
    public function enableCache(bool $enable = true): self
    {
        $this->enableCache = $enable;
        return $this;
    }
    
    public function isCacheEnabled(): bool
    {
        return $this->enableCache;
    }
    
    public function setCacheTTL(int $ttl): self
    {
        $this->cacheTTL = $ttl;
        return $this;
    }
    
    public function getCacheTTL(): int
    {
        return $this->cacheTTL;
    }
    
    public function addEntityPath(string $path, string $namespace): self
    {
        $this->entityPaths[] = ['path' => $path, 'namespace' => $namespace];
        return $this;
    }
    
    public function getEntityPaths(): array
    {
        return $this->entityPaths;
    }
    
    public function setMigrationPath(string $path): self
    {
        $this->migrationPath = $path;
        return $this;
    }
    
    public function getMigrationPath(): string
    {
        return $this->migrationPath;
    }
    
    public function addListener(string $event, callable $listener): self
    {
        if (!isset($this->listeners[$event])) {
            $this->listeners[$event] = [];
        }
        $this->listeners[$event][] = $listener;
        return $this;
    }
    
    public function getListeners(string $event): array
    {
        return $this->listeners[$event] ?? [];
    }
    
    public static function create(): self
    {
        return new self();
    }
}

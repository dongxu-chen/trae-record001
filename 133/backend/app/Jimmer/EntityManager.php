<?php

namespace App\Jimmer;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Cache;
use App\Jimmer\Mapping\EntityMetadata;
use App\Jimmer\Query\QueryBuilder;
use App\Jimmer\Schema\SchemaManager;
use App\Jimmer\Encryption\EncryptionManager;

class EntityManager
{
    protected static $instance = null;
    
    protected $config;
    protected $connection;
    protected $metadataFactory;
    protected $schemaManager;
    protected $encryptionManager;
    protected $unitOfWork;
    
    protected $entities = [];
    protected $pendingInserts = [];
    protected $pendingUpdates = [];
    protected $pendingDeletes = [];
    
    protected function __construct(JimmerConfig $config)
    {
        $this->config = $config;
        $this->connection = DB::connection($config->getConnectionName());
        $this->metadataFactory = new MetadataFactory($config);
        $this->schemaManager = new SchemaManager($this);
        $this->encryptionManager = new EncryptionManager($config);
        $this->unitOfWork = new UnitOfWork($this);
    }
    
    public static function getInstance(?JimmerConfig $config = null): self
    {
        if (self::$instance === null) {
            if ($config === null) {
                $config = JimmerConfig::create();
            }
            self::$instance = new self($config);
        }
        return self::$instance;
    }
    
    public function getConfig(): JimmerConfig
    {
        return $this->config;
    }
    
    public function getConnection()
    {
        return $this->connection;
    }
    
    public function getMetadataFactory(): MetadataFactory
    {
        return $this->metadataFactory;
    }
    
    public function getSchemaManager(): SchemaManager
    {
        return $this->schemaManager;
    }
    
    public function getEncryptionManager(): EncryptionManager
    {
        return $this->encryptionManager;
    }
    
    public function getUnitOfWork(): UnitOfWork
    {
        return $this->unitOfWork;
    }
    
    public function createQueryBuilder(string $entityClass): QueryBuilder
    {
        return new QueryBuilder($this, $entityClass);
    }
    
    public function find(string $entityClass, $id, array $fetchGroups = [])
    {
        $metadata = $this->metadataFactory->getMetadata($entityClass);
        
        $cacheKey = $this->getCacheKey($entityClass, $id);
        if ($this->config->isCacheEnabled() && Cache::has($cacheKey)) {
            return Cache::get($cacheKey);
        }
        
        $qb = $this->createQueryBuilder($entityClass)
            ->where($metadata->getIdField()->name, '=', $id);
        
        if (!empty($fetchGroups)) {
            foreach ($fetchGroups as $fetchGroup) {
                $qb->fetch($fetchGroup);
            }
        }
        
        $entity = $qb->first();
        
        if ($entity && $this->config->isCacheEnabled()) {
            Cache::put($cacheKey, $entity, $this->config->getCacheTTL());
        }
        
        return $entity;
    }
    
    public function findAll(string $entityClass, array $fetchGroups = []): array
    {
        $qb = $this->createQueryBuilder($entityClass);
        
        if (!empty($fetchGroups)) {
            foreach ($fetchGroups as $fetchGroup) {
                $qb->fetch($fetchGroup);
            }
        }
        
        return $qb->get();
    }
    
    public function persist(object $entity): void
    {
        $this->unitOfWork->persist($entity);
    }
    
    public function remove(object $entity): void
    {
        $this->unitOfWork->remove($entity);
    }
    
    public function merge(object $entity): object
    {
        return $this->unitOfWork->merge($entity);
    }
    
    public function flush(): void
    {
        $this->unitOfWork->commit();
    }
    
    public function refresh(object $entity): void
    {
        $this->unitOfWork->refresh($entity);
    }
    
    public function detach(object $entity): void
    {
        $this->unitOfWork->detach($entity);
    }
    
    public function clear(?string $entityClass = null): void
    {
        $this->unitOfWork->clear($entityClass);
    }
    
    public function transactional(callable $func)
    {
        return $this->connection->transaction(function () use ($func) {
            $result = $func($this);
            $this->flush();
            return $result;
        });
    }
    
    public function createRepository(string $entityClass): Repository
    {
        $metadata = $this->metadataFactory->getMetadata($entityClass);
        $repositoryClass = $metadata->repositoryClass ?? Repository::class;
        return new $repositoryClass($this, $entityClass);
    }
    
    public function evictFromCache(string $entityClass, $id): void
    {
        $cacheKey = $this->getCacheKey($entityClass, $id);
        Cache::forget($cacheKey);
    }
    
    public function clearEntityCache(string $entityClass): void
    {
        $prefix = 'jimmer:' . str_replace('\\', ':', $entityClass) . ':';
        Cache::store('file')->getRedis()->del(
            array_keys(Cache::getStore()->getRedis()->keys("*{$prefix}*"))
        );
    }
    
    protected function getCacheKey(string $entityClass, $id): string
    {
        return 'jimmer:' . str_replace('\\', ':', $entityClass) . ':' . $id;
    }
    
    public function switchConnection(string $connectionName): void
    {
        $this->connection = DB::connection($connectionName);
        $this->config->setConnectionName($connectionName);
        $this->unitOfWork->clear();
    }
    
    public function createTenantTables(string $tenantId): void
    {
        $this->schemaManager->createTenantTables($tenantId);
    }
    
    public function dropTenantTables(string $tenantId): void
    {
        $this->schemaManager->dropTenantTables($tenantId);
    }
    
    public static function resetInstance(): void
    {
        self::$instance = null;
    }
}

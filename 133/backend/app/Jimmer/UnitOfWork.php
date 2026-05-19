<?php

namespace App\Jimmer;

use SplObjectStorage;

class UnitOfWork
{
    const STATE_NEW = 'new';
    const STATE_MANAGED = 'managed';
    const STATE_DETACHED = 'detached';
    const STATE_REMOVED = 'removed';
    
    protected $entityManager;
    protected $metadataFactory;
    protected $encryptionManager;
    
    protected $entities;
    protected $entityStates;
    protected $entityData;
    
    protected $pendingInserts = [];
    protected $pendingUpdates = [];
    protected $pendingDeletes = [];
    
    protected $collectionUpdates = [];
    
    public function __construct(EntityManager $entityManager)
    {
        $this->entityManager = $entityManager;
        $this->metadataFactory = $entityManager->getMetadataFactory();
        $this->encryptionManager = $entityManager->getEncryptionManager();
        $this->entities = new SplObjectStorage();
        $this->entityStates = new SplObjectStorage();
        $this->entityData = new SplObjectStorage();
    }
    
    public function persist(object $entity): void
    {
        $state = $this->getEntityState($entity);
        
        if ($state === self::STATE_MANAGED) {
            return;
        }
        
        if ($state === self::STATE_NEW) {
            $oid = spl_object_hash($entity);
            $this->pendingInserts[$oid] = $entity;
            $this->entityStates[$entity] = self::STATE_MANAGED;
            $this->entities[$entity] = true;
        }
    }
    
    public function remove(object $entity): void
    {
        $state = $this->getEntityState($entity);
        
        if ($state === self::STATE_REMOVED) {
            return;
        }
        
        $oid = spl_object_hash($entity);
        $this->pendingDeletes[$oid] = $entity;
        $this->entityStates[$entity] = self::STATE_REMOVED;
    }
    
    public function merge(object $entity): object
    {
        $metadata = $this->metadataFactory->getMetadata(get_class($entity));
        $id = $metadata->getIdValue($entity);
        
        if ($id === null) {
            $this->persist($entity);
            return $entity;
        }
        
        $managedEntity = $this->entityManager->find(get_class($entity), $id);
        
        if ($managedEntity === null) {
            $this->persist($entity);
            return $entity;
        }
        
        foreach ($metadata->fields as $field) {
            $value = $metadata->getFieldValue($entity, $field->name);
            $metadata->setFieldValue($managedEntity, $field->name, $value);
        }
        
        return $managedEntity;
    }
    
    public function refresh(object $entity): void
    {
        $metadata = $this->metadataFactory->getMetadata(get_class($entity));
        $id = $metadata->getIdValue($entity);
        
        if ($id === null) {
            throw new \RuntimeException('Entity has no identity');
        }
        
        $qb = $this->entityManager->createQueryBuilder(get_class($entity));
        $freshEntity = $qb->where($metadata->idField->name, '=', $id)->first();
        
        if ($freshEntity === null) {
            throw new \RuntimeException('Entity not found');
        }
        
        foreach ($metadata->fields as $field) {
            $value = $metadata->getFieldValue($freshEntity, $field->name);
            $metadata->setFieldValue($entity, $field->name, $value);
        }
    }
    
    public function detach(object $entity): void
    {
        $oid = spl_object_hash($entity);
        
        unset($this->pendingInserts[$oid]);
        unset($this->pendingUpdates[$oid]);
        unset($this->pendingDeletes[$oid]);
        
        if (isset($this->entityStates[$entity])) {
            unset($this->entityStates[$entity]);
        }
        
        if (isset($this->entities[$entity])) {
            unset($this->entities[$entity]);
        }
    }
    
    public function clear(?string $entityClass = null): void
    {
        if ($entityClass === null) {
            $this->pendingInserts = [];
            $this->pendingUpdates = [];
            $this->pendingDeletes = [];
            $this->entities = new SplObjectStorage();
            $this->entityStates = new SplObjectStorage();
            $this->entityData = new SplObjectStorage();
        } else {
            foreach ($this->entities as $entity) {
                if ($entity instanceof $entityClass) {
                    $this->detach($entity);
                }
            }
        }
    }
    
    public function commit(): void
    {
        $this->executeInserts();
        $this->executeUpdates();
        $this->executeDeletes();
        $this->executeCollectionUpdates();
    }
    
    protected function executeInserts(): void
    {
        foreach ($this->pendingInserts as $oid => $entity) {
            $metadata = $this->metadataFactory->getMetadata(get_class($entity));
            $tableName = $this->getTableName($metadata, $entity);
            
            $data = $this->prepareInsertData($entity, $metadata);
            
            $this->entityManager->getConnection()
                ->table($tableName)
                ->insert($data);
            
            $lastId = $this->entityManager->getConnection()->getPdo()->lastInsertId();
            $metadata->setIdValue($entity, $lastId);
            
            $this->entityData[$entity] = $this->getOriginalData($entity, $metadata);
        }
        
        $this->pendingInserts = [];
    }
    
    protected function executeUpdates(): void
    {
        foreach ($this->pendingUpdates as $oid => $entity) {
            $metadata = $this->metadataFactory->getMetadata(get_class($entity));
            $tableName = $this->getTableName($metadata, $entity);
            
            $data = $this->prepareUpdateData($entity, $metadata);
            
            if (!empty($data)) {
                $idField = $metadata->idField->name;
                $idValue = $metadata->getIdValue($entity);
                
                $this->entityManager->getConnection()
                    ->table($tableName)
                    ->where($idField, '=', $idValue)
                    ->update($data);
                
                $this->entityData[$entity] = $this->getOriginalData($entity, $metadata);
            }
        }
        
        $this->pendingUpdates = [];
    }
    
    protected function executeDeletes(): void
    {
        foreach ($this->pendingDeletes as $oid => $entity) {
            $metadata = $this->metadataFactory->getMetadata(get_class($entity));
            $tableName = $this->getTableName($metadata, $entity);
            
            $idField = $metadata->idField->name;
            $idValue = $metadata->getIdValue($entity);
            
            $this->entityManager->getConnection()
                ->table($tableName)
                ->where($idField, '=', $idValue)
                ->delete();
            
            $this->detach($entity);
        }
        
        $this->pendingDeletes = [];
    }
    
    protected function executeCollectionUpdates(): void
    {
        foreach ($this->collectionUpdates as $update) {
        }
        
        $this->collectionUpdates = [];
    }
    
    protected function prepareInsertData(object $entity, $metadata): array
    {
        $data = [];
        
        foreach ($metadata->fields as $field) {
            if ($field->isGeneratedValue) {
                continue;
            }
            
            $value = $metadata->getFieldValue($entity, $field->name);
            
            if ($field->isEncrypted && $value !== null) {
                $value = $this->encryptionManager->encrypt($value);
            }
            
            if ($field->type === 'json' && is_array($value)) {
                $value = json_encode($value);
            }
            
            if ($field->type === 'datetime' && $value instanceof \DateTimeInterface) {
                $value = $value->format('Y-m-d H:i:s');
            }
            
            if ($value === null && !$field->isNullable) {
                continue;
            }
            
            $data[$field->columnName] = $value;
        }
        
        return $data;
    }
    
    protected function prepareUpdateData(object $entity, $metadata): array
    {
        $data = [];
        $originalData = $this->entityData[$entity] ?? [];
        
        foreach ($metadata->fields as $field) {
            if ($field->isId) {
                continue;
            }
            
            $value = $metadata->getFieldValue($entity, $field->name);
            $originalValue = $originalData[$field->name] ?? null;
            
            if ($value !== $originalValue) {
                if ($field->isEncrypted && $value !== null) {
                    $value = $this->encryptionManager->encrypt($value);
                }
                
                if ($field->type === 'json' && is_array($value)) {
                    $value = json_encode($value);
                }
                
                if ($field->type === 'datetime' && $value instanceof \DateTimeInterface) {
                    $value = $value->format('Y-m-d H:i:s');
                }
                
                $data[$field->columnName] = $value;
            }
        }
        
        return $data;
    }
    
    protected function getOriginalData(object $entity, $metadata): array
    {
        $data = [];
        
        foreach ($metadata->fields as $field) {
            $data[$field->name] = $metadata->getFieldValue($entity, $field->name);
        }
        
        return $data;
    }
    
    protected function getTableName($metadata, object $entity): string
    {
        if ($metadata->isTenantAware) {
            $tenantId = $this->getEntityTenantId($entity, $metadata);
            if ($tenantId) {
                return $metadata->getTenantTableName($tenantId);
            }
        }
        
        return $metadata->getFullTableName();
    }
    
    protected function getEntityTenantId(object $entity, $metadata): ?string
    {
        foreach ($metadata->fields as $field) {
            if ($field->isTenantId) {
                return $metadata->getFieldValue($entity, $field->name);
            }
        }
        
        return null;
    }
    
    public function getEntityState(object $entity): string
    {
        if (isset($this->entityStates[$entity])) {
            return $this->entityStates[$entity];
        }
        
        $metadata = $this->metadataFactory->getMetadata(get_class($entity));
        $id = $metadata->getIdValue($entity);
        
        if ($id === null) {
            return self::STATE_NEW;
        }
        
        return self::STATE_DETACHED;
    }
    
    public function isEntityManaged(object $entity): bool
    {
        return isset($this->entities[$entity]);
    }
    
    public function scheduleForUpdate(object $entity): void
    {
        $oid = spl_object_hash($entity);
        
        if (!isset($this->pendingUpdates[$oid]) && !isset($this->pendingInserts[$oid])) {
            $this->pendingUpdates[$oid] = $entity;
        }
    }
    
    public function getScheduledEntityInsertions(): array
    {
        return array_values($this->pendingInserts);
    }
    
    public function getScheduledEntityUpdates(): array
    {
        return array_values($this->pendingUpdates);
    }
    
    public function getScheduledEntityDeletions(): array
    {
        return array_values($this->pendingDeletes);
    }
}

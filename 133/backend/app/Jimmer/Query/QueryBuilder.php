<?php

namespace App\Jimmer\Query;

use App\Jimmer\EntityManager;
use App\Jimmer\Mapping\EntityMetadata;
use Illuminate\Database\Query\Builder;

class QueryBuilder
{
    protected $entityManager;
    protected $metadata;
    protected $entityClass;
    protected $query;
    protected $connection;
    
    protected $selects = ['*'];
    protected $wheres = [];
    protected $joins = [];
    protected $orders = [];
    protected $groups = [];
    protected $havings = [];
    protected $limit;
    protected $offset;
    
    protected $fetchAssociations = [];
    protected $eagerLoads = [];
    
    protected $parameters = [];
    protected $tenantId;
    
    public function __construct(EntityManager $entityManager, string $entityClass)
    {
        $this->entityManager = $entityManager;
        $this->entityClass = $entityClass;
        $this->metadata = $entityManager->getMetadataFactory()->getMetadata($entityClass);
        $this->connection = $entityManager->getConnection();
        $this->query = $this->connection->table($this->getTableName());
    }
    
    protected function getTableName(): string
    {
        if ($this->tenantId) {
            return $this->metadata->getTenantTableName($this->tenantId);
        }
        return $this->metadata->getFullTableName();
    }
    
    public function forTenant(string $tenantId): self
    {
        $this->tenantId = $tenantId;
        $this->query = $this->connection->table($this->getTableName());
        return $this;
    }
    
    public function select($columns = ['*']): self
    {
        $this->selects = is_array($columns) ? $columns : func_get_args();
        $this->query->select($this->selects);
        return $this;
    }
    
    public function where(string $column, string $operator = null, $value = null, string $boolean = 'and'): self
    {
        if (func_num_args() === 2) {
            $value = $operator;
            $operator = '=';
        }
        
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->where($columnName, $operator, $value, $boolean);
        return $this;
    }
    
    public function orWhere(string $column, string $operator = null, $value = null): self
    {
        return $this->where($column, $operator, $value, 'or');
    }
    
    public function whereIn(string $column, array $values, string $boolean = 'and', bool $not = false): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->whereIn($columnName, $values, $boolean, $not);
        return $this;
    }
    
    public function whereNotIn(string $column, array $values, string $boolean = 'and'): self
    {
        return $this->whereIn($column, $values, $boolean, true);
    }
    
    public function whereBetween(string $column, array $values, string $boolean = 'and', bool $not = false): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->whereBetween($columnName, $values, $boolean, $not);
        return $this;
    }
    
    public function whereNotBetween(string $column, array $values, string $boolean = 'and'): self
    {
        return $this->whereBetween($column, $values, $boolean, true);
    }
    
    public function whereNull(string $column, string $boolean = 'and', bool $not = false): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->whereNull($columnName, $boolean, $not);
        return $this;
    }
    
    public function whereNotNull(string $column, string $boolean = 'and'): self
    {
        return $this->whereNull($column, $boolean, true);
    }
    
    public function whereLike(string $column, string $value, string $boolean = 'and'): self
    {
        return $this->where($column, 'LIKE', $value, $boolean);
    }
    
    public function orWhereLike(string $column, string $value): self
    {
        return $this->whereLike($column, $value, 'or');
    }
    
    public function whereRaw(string $sql, array $bindings = [], string $boolean = 'and'): self
    {
        $this->query->whereRaw($sql, $bindings, $boolean);
        return $this;
    }
    
    public function whereGroup(\Closure $callback, string $boolean = 'and'): self
    {
        $this->query->where(function ($query) use ($callback) {
            $subBuilder = new static($this->entityManager, $this->entityClass);
            $subBuilder->query = $query;
            $callback($subBuilder);
        }, null, null, $boolean);
        
        return $this;
    }
    
    public function predicate(Predicate $predicate): self
    {
        $predicate->apply($this);
        return $this;
    }
    
    public function join(string $relatedEntity, string $first, string $operator = null, string $second = null, string $type = 'inner'): self
    {
        $relatedMetadata = $this->entityManager->getMetadataFactory()->getMetadata($relatedEntity);
        $relatedTable = $relatedMetadata->getFullTableName();
        
        $this->query->join($relatedTable, $first, $operator, $second, $type);
        return $this;
    }
    
    public function leftJoin(string $relatedEntity, string $first, string $operator = null, string $second = null): self
    {
        return $this->join($relatedEntity, $first, $operator, $second, 'left');
    }
    
    public function rightJoin(string $relatedEntity, string $first, string $operator = null, string $second = null): self
    {
        return $this->join($relatedEntity, $first, $operator, $second, 'right');
    }
    
    public function fetch(string $association): self
    {
        if ($this->metadata->hasAssociation($association)) {
            $this->fetchAssociations[] = $association;
        }
        return $this;
    }
    
    public function orderBy(string $column, string $direction = 'asc'): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->orderBy($columnName, $direction);
        return $this;
    }
    
    public function orderByDesc(string $column): self
    {
        return $this->orderBy($column, 'desc');
    }
    
    public function groupBy(string $column): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->groupBy($columnName);
        return $this;
    }
    
    public function having(string $column, string $operator = null, $value = null): self
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $this->query->having($columnName, $operator, $value);
        return $this;
    }
    
    public function limit(int $limit): self
    {
        $this->query->limit($limit);
        return $this;
    }
    
    public function offset(int $offset): self
    {
        $this->query->offset($offset);
        return $this;
    }
    
    public function take(int $count): self
    {
        return $this->limit($count);
    }
    
    public function skip(int $count): self
    {
        return $this->offset($count);
    }
    
    public function forPage(int $page, int $perPage = 15): self
    {
        return $this->skip(($page - 1) * $perPage)->take($perPage);
    }
    
    public function get(): array
    {
        $results = $this->query->get();
        
        if ($results->isEmpty()) {
            return [];
        }
        
        $entities = [];
        $encryptionManager = $this->entityManager->getEncryptionManager();
        
        foreach ($results as $row) {
            $entity = $this->hydrateEntity((array)$row, $encryptionManager);
            $entities[] = $entity;
        }
        
        if (!empty($this->fetchAssociations)) {
            $this->eagerLoadAssociations($entities);
        }
        
        return $entities;
    }
    
    public function first()
    {
        $result = $this->query->first();
        
        if (!$result) {
            return null;
        }
        
        $encryptionManager = $this->entityManager->getEncryptionManager();
        $entity = $this->hydrateEntity((array)$result, $encryptionManager);
        
        if (!empty($this->fetchAssociations)) {
            $this->eagerLoadAssociations([$entity]);
        }
        
        return $entity;
    }
    
    public function find($id)
    {
        $idField = $this->metadata->idField->name;
        return $this->where($idField, '=', $id)->first();
    }
    
    public function findMany(array $ids): array
    {
        $idField = $this->metadata->idField->name;
        return $this->whereIn($idField, $ids)->get();
    }
    
    public function count(string $column = '*'): int
    {
        return $this->query->count($column);
    }
    
    public function sum(string $column)
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        return $this->query->sum($columnName);
    }
    
    public function avg(string $column)
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        return $this->query->avg($columnName);
    }
    
    public function min(string $column)
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        return $this->query->min($columnName);
    }
    
    public function max(string $column)
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        return $this->query->max($columnName);
    }
    
    public function exists(): bool
    {
        return $this->query->exists();
    }
    
    public function paginate(int $perPage = 15, int $page = 1): array
    {
        $total = $this->count();
        $items = $this->forPage($page, $perPage)->get();
        
        return [
            'items' => $items,
            'total' => $total,
            'per_page' => $perPage,
            'current_page' => $page,
            'last_page' => (int)ceil($total / $perPage),
        ];
    }
    
    public function chunk(int $count, \Closure $callback): bool
    {
        $page = 1;
        
        do {
            $results = $this->forPage($page, $count)->get();
            
            if (empty($results)) {
                break;
            }
            
            if ($callback($results, $page) === false) {
                return false;
            }
            
            $page++;
        } while (count($results) === $count);
        
        return true;
    }
    
    public function pluck(string $column, ?string $key = null): array
    {
        $field = $this->metadata->getField($column);
        $columnName = $field ? $field->columnName : $column;
        
        $keyColumnName = null;
        if ($key) {
            $keyField = $this->metadata->getField($key);
            $keyColumnName = $keyField ? $keyField->columnName : $key;
        }
        
        return $this->query->pluck($columnName, $keyColumnName)->all();
    }
    
    protected function hydrateEntity(array $data, $encryptionManager): object
    {
        $className = $this->entityClass;
        $entity = new $className();
        
        foreach ($this->metadata->fields as $field) {
            $columnName = $field->columnName;
            
            if (array_key_exists($columnName, $data)) {
                $value = $data[$columnName];
                
                if ($field->isEncrypted && $value !== null) {
                    $value = $encryptionManager->decrypt($value);
                }
                
                if ($field->type === 'json' && is_string($value)) {
                    $value = json_decode($value, true);
                }
                
                if ($field->type === 'datetime' && is_string($value)) {
                    $value = new \DateTimeImmutable($value);
                }
                
                $this->metadata->setFieldValue($entity, $field->name, $value);
            }
        }
        
        return $entity;
    }
    
    protected function eagerLoadAssociations(array $entities): void
    {
        if (empty($entities)) {
            return;
        }
        
        foreach ($this->fetchAssociations as $associationName) {
            $this->eagerLoadAssociation($entities, $associationName);
        }
    }
    
    protected function eagerLoadAssociation(array $entities, string $associationName): void
    {
        $association = $this->metadata->getAssociation($associationName);
        if (!$association) {
            return;
        }
        
        $relatedMetadata = $this->entityManager->getMetadataFactory()->getMetadata($association->targetEntity);
        
        $ids = [];
        foreach ($entities as $entity) {
            $id = $this->metadata->getIdValue($entity);
            if ($id !== null) {
                $ids[] = $id;
            }
        }
        
        if (empty($ids)) {
            return;
        }
        
        $relatedQuery = $this->entityManager->createQueryBuilder($association->targetEntity);
        
        if ($association->type === 'one_to_many') {
            $mappedByField = $relatedMetadata->getField($association->mappedBy);
            if ($mappedByField) {
                $relatedQuery->whereIn($mappedByField->columnName, $ids);
            }
        } elseif ($association->type === 'many_to_one') {
            $joinColumn = $association->getJoinColumnName();
            $relatedIds = [];
            foreach ($entities as $entity) {
                $idValue = $this->metadata->getFieldValue($entity, $associationName . '_id');
                if ($idValue !== null) {
                    $relatedIds[] = $idValue;
                }
            }
            if (!empty($relatedIds)) {
                $relatedQuery->whereIn($relatedMetadata->idField->name, array_unique($relatedIds));
            }
        } elseif ($association->type === 'many_to_many') {
        }
        
        $relatedEntities = $relatedQuery->get();
        
        $indexed = [];
        foreach ($relatedEntities as $related) {
            $relatedId = $relatedMetadata->getIdValue($related);
            $indexed[$relatedId] = $related;
        }
        
        foreach ($entities as $entity) {
            $this->associateEntities($entity, $indexed, $association);
        }
    }
    
    protected function associateEntities(object $entity, array $relatedEntities, $association): void
    {
        $entityId = $this->metadata->getIdValue($entity);
        
        if ($association->type === 'many_to_one') {
            $foreignKey = $association->getJoinColumnName();
            $relatedId = $this->metadata->getFieldValue($entity, $association->fieldName . '_id');
            
            if (isset($relatedEntities[$relatedId])) {
                $this->metadata->setFieldValue($entity, $association->fieldName, $relatedEntities[$relatedId]);
            }
        }
    }
    
    public function toSql(): string
    {
        return $this->query->toSql();
    }
    
    public function getBindings(): array
    {
        return $this->query->getBindings();
    }
    
    public function getQuery(): Builder
    {
        return $this->query;
    }
    
    public function when($value, \Closure $callback, ?\Closure $default = null): self
    {
        if ($value) {
            $callback($this, $value);
        } elseif ($default) {
            $default($this, $value);
        }
        
        return $this;
    }
    
    public function unless($value, \Closure $callback, ?\Closure $default = null): self
    {
        return $this->when(!$value, $callback, $default);
    }
    
    public function distinct(): self
    {
        $this->query->distinct();
        return $this;
    }
}

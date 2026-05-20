<?php

namespace App\Jimmer;

use App\Jimmer\Query\Predicate;

class Repository
{
    protected $entityManager;
    protected $entityClass;
    protected $metadata;
    
    public function __construct(EntityManager $entityManager, string $entityClass)
    {
        $this->entityManager = $entityManager;
        $this->entityClass = $entityClass;
        $this->metadata = $entityManager->getMetadataFactory()->getMetadata($entityClass);
    }
    
    public function createQueryBuilder(): Query\QueryBuilder
    {
        return $this->entityManager->createQueryBuilder($this->entityClass);
    }
    
    public function find($id, array $fetchGroups = [])
    {
        return $this->entityManager->find($this->entityClass, $id, $fetchGroups);
    }
    
    public function findAll(array $fetchGroups = []): array
    {
        return $this->entityManager->findAll($this->entityClass, $fetchGroups);
    }
    
    public function findBy(array $criteria, ?array $orderBy = null, ?int $limit = null, ?int $offset = null): array
    {
        $qb = $this->createQueryBuilder();
        
        foreach ($criteria as $field => $value) {
            if (is_array($value)) {
                $qb->whereIn($field, $value);
            } elseif ($value === null) {
                $qb->whereNull($field);
            } else {
                $qb->where($field, '=', $value);
            }
        }
        
        if ($orderBy) {
            foreach ($orderBy as $field => $direction) {
                $qb->orderBy($field, $direction);
            }
        }
        
        if ($limit) {
            $qb->limit($limit);
        }
        
        if ($offset) {
            $qb->offset($offset);
        }
        
        return $qb->get();
    }
    
    public function findOneBy(array $criteria)
    {
        return $this->createQueryBuilder()
            ->predicate($this->buildPredicate($criteria))
            ->first();
    }
    
    protected function buildPredicate(array $criteria): Predicate
    {
        $predicates = [];
        
        foreach ($criteria as $field => $value) {
            if (is_array($value)) {
                $predicates[] = Predicate::in($field, $value);
            } elseif ($value === null) {
                $predicates[] = Predicate::isNull($field);
            } else {
                $predicates[] = Predicate::eq($field, $value);
            }
        }
        
        return Predicate::and(...$predicates);
    }
    
    public function count(array $criteria = []): int
    {
        $qb = $this->createQueryBuilder();
        
        foreach ($criteria as $field => $value) {
            if (is_array($value)) {
                $qb->whereIn($field, $value);
            } elseif ($value === null) {
                $qb->whereNull($field);
            } else {
                $qb->where($field, '=', $value);
            }
        }
        
        return $qb->count();
    }
    
    public function save(object $entity): void
    {
        $this->entityManager->persist($entity);
    }
    
    public function delete(object $entity): void
    {
        $this->entityManager->remove($entity);
    }
    
    public function flush(): void
    {
        $this->entityManager->flush();
    }
    
    public function paginate(int $page = 1, int $perPage = 15, array $criteria = [], ?array $orderBy = null): array
    {
        $qb = $this->createQueryBuilder();
        
        foreach ($criteria as $field => $value) {
            if (is_array($value)) {
                $qb->whereIn($field, $value);
            } elseif ($value === null) {
                $qb->whereNull($field);
            } else {
                $qb->where($field, '=', $value);
            }
        }
        
        if ($orderBy) {
            foreach ($orderBy as $field => $direction) {
                $qb->orderBy($field, $direction);
            }
        }
        
        return $qb->paginate($perPage, $page);
    }
    
    public function exists(array $criteria): bool
    {
        return $this->createQueryBuilder()
            ->predicate($this->buildPredicate($criteria))
            ->exists();
    }
    
    public function aggregate(string $function, string $column, array $criteria = [])
    {
        $qb = $this->createQueryBuilder();
        
        foreach ($criteria as $field => $value) {
            if (is_array($value)) {
                $qb->whereIn($field, $value);
            } elseif ($value === null) {
                $qb->whereNull($field);
            } else {
                $qb->where($field, '=', $value);
            }
        }
        
        return $qb->{$function}($column);
    }
    
    public function sum(string $column, array $criteria = [])
    {
        return $this->aggregate('sum', $column, $criteria);
    }
    
    public function avg(string $column, array $criteria = [])
    {
        return $this->aggregate('avg', $column, $criteria);
    }
    
    public function min(string $column, array $criteria = [])
    {
        return $this->aggregate('min', $column, $criteria);
    }
    
    public function max(string $column, array $criteria = [])
    {
        return $this->aggregate('max', $column, $criteria);
    }
    
    public function getEntityManager(): EntityManager
    {
        return $this->entityManager;
    }
    
    public function getEntityClass(): string
    {
        return $this->entityClass;
    }
}

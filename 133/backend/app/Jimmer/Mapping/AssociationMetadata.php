<?php

namespace App\Jimmer\Mapping;

class AssociationMetadata
{
    const ONE_TO_ONE = 'one_to_one';
    const ONE_TO_MANY = 'one_to_many';
    const MANY_TO_ONE = 'many_to_one';
    const MANY_TO_MANY = 'many_to_many';
    
    public $fieldName;
    public $type;
    public $targetEntity;
    public $mappedBy;
    public $inversedBy;
    public $joinColumn;
    public $joinTable;
    public $isOwningSide = true;
    public $fetchStrategy = 'lazy';
    public $cascade = [];
    public $orphanRemoval = false;
    public $orderBy = [];
    public $indexBy;
    
    public function __construct(string $fieldName, string $type)
    {
        $this->fieldName = $fieldName;
        $this->type = $type;
    }
    
    public function setTargetEntity(string $targetEntity): self
    {
        $this->targetEntity = $targetEntity;
        return $this;
    }
    
    public function setMappedBy(?string $mappedBy): self
    {
        $this->mappedBy = $mappedBy;
        $this->isOwningSide = $mappedBy === null;
        return $this;
    }
    
    public function setInversedBy(?string $inversedBy): self
    {
        $this->inversedBy = $inversedBy;
        return $this;
    }
    
    public function setJoinColumn(array $joinColumn): self
    {
        $this->joinColumn = array_merge([
            'name' => null,
            'referencedColumnName' => 'id',
            'nullable' => true,
            'unique' => false,
            'onDelete' => null,
            'onUpdate' => null,
        ], $joinColumn);
        return $this;
    }
    
    public function setJoinTable(array $joinTable): self
    {
        $this->joinTable = array_merge([
            'name' => null,
            'joinColumns' => [],
            'inverseJoinColumns' => [],
        ], $joinTable);
        return $this;
    }
    
    public function setFetchStrategy(string $strategy): self
    {
        $this->fetchStrategy = $strategy;
        return $this;
    }
    
    public function setCascade(array $cascade): self
    {
        $this->cascade = $cascade;
        return $this;
    }
    
    public function setOrphanRemoval(bool $orphanRemoval): self
    {
        $this->orphanRemoval = $orphanRemoval;
        return $this;
    }
    
    public function setOrderBy(array $orderBy): self
    {
        $this->orderBy = $orderBy;
        return $this;
    }
    
    public function setIndexBy(?string $indexBy): self
    {
        $this->indexBy = $indexBy;
        return $this;
    }
    
    public function isCollection(): bool
    {
        return in_array($this->type, [self::ONE_TO_MANY, self::MANY_TO_MANY]);
    }
    
    public function getJoinColumnName(): string
    {
        if ($this->joinColumn && $this->joinColumn['name']) {
            return $this->joinColumn['name'];
        }
        
        return $this->fieldName . '_id';
    }
    
    public function getJoinTableName(string $sourceTable, string $targetTable): string
    {
        if ($this->joinTable && $this->joinTable['name']) {
            return $this->joinTable['name'];
        }
        
        $tables = [$sourceTable, $targetTable];
        sort($tables);
        return implode('_', $tables);
    }
    
    public function shouldCascade(string $operation): bool
    {
        return in_array('all', $this->cascade) || in_array($operation, $this->cascade);
    }
    
    public static function createOneToOne(string $fieldName): self
    {
        return new self($fieldName, self::ONE_TO_ONE);
    }
    
    public static function createOneToMany(string $fieldName): self
    {
        return new self($fieldName, self::ONE_TO_MANY);
    }
    
    public static function createManyToOne(string $fieldName): self
    {
        return new self($fieldName, self::MANY_TO_ONE);
    }
    
    public static function createManyToMany(string $fieldName): self
    {
        return new self($fieldName, self::MANY_TO_MANY);
    }
}

<?php

namespace App\Jimmer\Mapping;

class EntityMetadata
{
    public $className;
    public $tableName;
    public $schemaName;
    public $tablePrefix = '';
    public $isTenantAware = false;
    public $repositoryClass;
    public $idField;
    public $fields = [];
    public $associations = [];
    public $embeddedClasses = [];
    public $lifecycleCallbacks = [];
    public $encryptedFields = [];
    
    protected $fieldMap = [];
    protected $associationMap = [];
    
    public function __construct(string $className)
    {
        $this->className = $className;
    }
    
    public function getFullTableName(): string
    {
        return $this->tablePrefix . $this->tableName;
    }
    
    public function getTenantTableName(string $tenantId): string
    {
        return $this->tablePrefix . $tenantId . '_' . $this->tableName;
    }
    
    public function addField(FieldMetadata $field): void
    {
        $this->fields[] = $field;
        $this->fieldMap[$field->name] = $field;
        
        if ($field->isId) {
            $this->idField = $field;
        }
        
        if ($field->isEncrypted) {
            $this->encryptedFields[] = $field->name;
        }
    }
    
    public function getField(string $name): ?FieldMetadata
    {
        return $this->fieldMap[$name] ?? null;
    }
    
    public function hasField(string $name): bool
    {
        return isset($this->fieldMap[$name]);
    }
    
    public function addAssociation(AssociationMetadata $association): void
    {
        $this->associations[] = $association;
        $this->associationMap[$association->fieldName] = $association;
    }
    
    public function getAssociation(string $fieldName): ?AssociationMetadata
    {
        return $this->associationMap[$fieldName] ?? null;
    }
    
    public function hasAssociation(string $fieldName): bool
    {
        return isset($this->associationMap[$fieldName]);
    }
    
    public function getIdValue(object $entity)
    {
        if (!$this->idField) {
            return null;
        }
        
        $getter = 'get' . ucfirst($this->idField->name);
        if (method_exists($entity, $getter)) {
            return $entity->$getter();
        }
        
        return $entity->{$this->idField->name} ?? null;
    }
    
    public function setIdValue(object $entity, $value): void
    {
        if (!$this->idField) {
            return;
        }
        
        $setter = 'set' . ucfirst($this->idField->name);
        if (method_exists($entity, $setter)) {
            $entity->$setter($value);
        } else {
            $entity->{$this->idField->name} = $value;
        }
    }
    
    public function getFieldValue(object $entity, string $fieldName)
    {
        $getter = 'get' . ucfirst($fieldName);
        if (method_exists($entity, $getter)) {
            return $entity->$getter();
        }
        
        return $entity->$fieldName ?? null;
    }
    
    public function setFieldValue(object $entity, string $fieldName, $value): void
    {
        $setter = 'set' . ucfirst($fieldName);
        if (method_exists($entity, $setter)) {
            $entity->$setter($value);
        } else {
            $entity->$fieldName = $value;
        }
    }
    
    public function getColumnNames(): array
    {
        return array_map(function ($field) {
            return $field->columnName;
        }, $this->fields);
    }
    
    public function getFieldForColumn(string $columnName): ?FieldMetadata
    {
        foreach ($this->fields as $field) {
            if ($field->columnName === $columnName) {
                return $field;
            }
        }
        return null;
    }
    
    public function isEncryptedField(string $fieldName): bool
    {
        return in_array($fieldName, $this->encryptedFields);
    }
    
    public function getMappedFieldNames(): array
    {
        return array_keys($this->fieldMap);
    }
    
    public function getAssociationNames(): array
    {
        return array_keys($this->associationMap);
    }
}

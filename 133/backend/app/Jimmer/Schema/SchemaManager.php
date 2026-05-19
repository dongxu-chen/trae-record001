<?php

namespace App\Jimmer\Schema;

use App\Jimmer\EntityManager;
use App\Jimmer\Mapping\EntityMetadata;
use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;

class SchemaManager
{
    protected $entityManager;
    protected $metadataFactory;
    protected $connection;
    
    public function __construct(EntityManager $entityManager)
    {
        $this->entityManager = $entityManager;
        $this->metadataFactory = $entityManager->getMetadataFactory();
        $this->connection = $entityManager->getConnection();
    }
    
    public function createTenantTables(string $tenantId): void
    {
        $allMetadata = $this->metadataFactory->getAllMetadata();
        
        foreach ($allMetadata as $metadata) {
            if ($metadata->isTenantAware) {
                $this->createTenantTable($metadata, $tenantId);
            }
        }
    }
    
    public function createTenantTable(EntityMetadata $metadata, string $tenantId): void
    {
        $tableName = $metadata->getTenantTableName($tenantId);
        
        if (Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($tableName)) {
            return;
        }
        
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->create($tableName, function (Blueprint $table) use ($metadata) {
            $this->buildTableColumns($table, $metadata);
            $this->buildIndexes($table, $metadata);
            $this->buildForeignKeys($table, $metadata);
        });
    }
    
    public function dropTenantTables(string $tenantId): void
    {
        $allMetadata = $this->metadataFactory->getAllMetadata();
        
        foreach (array_reverse($allMetadata) as $metadata) {
            if ($metadata->isTenantAware) {
                $this->dropTenantTable($metadata, $tenantId);
            }
        }
    }
    
    public function dropTenantTable(EntityMetadata $metadata, string $tenantId): void
    {
        $tableName = $metadata->getTenantTableName($tenantId);
        
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->dropIfExists($tableName);
    }
    
    public function createTable(EntityMetadata $metadata): void
    {
        $tableName = $metadata->getFullTableName();
        
        if (Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($tableName)) {
            return;
        }
        
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->create($tableName, function (Blueprint $table) use ($metadata) {
            $this->buildTableColumns($table, $metadata);
            $this->buildIndexes($table, $metadata);
            $this->buildForeignKeys($table, $metadata);
        });
    }
    
    public function updateTable(EntityMetadata $metadata): void
    {
        $tableName = $metadata->getFullTableName();
        
        if (!Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($tableName)) {
            $this->createTable($metadata);
            return;
        }
        
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->table($tableName, function (Blueprint $table) use ($metadata) {
            $existingColumns = Schema::connection($this->entityManager->getConfig()->getConnectionName())->getColumnListing($table->getTable());
            
            foreach ($metadata->fields as $field) {
                if (!in_array($field->columnName, $existingColumns)) {
                    $this->addColumn($table, $field);
                }
            }
        });
    }
    
    public function dropTable(EntityMetadata $metadata): void
    {
        $tableName = $metadata->getFullTableName();
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->dropIfExists($tableName);
    }
    
    protected function buildTableColumns(Blueprint $table, EntityMetadata $metadata): void
    {
        foreach ($metadata->fields as $field) {
            $this->addColumn($table, $field);
        }
    }
    
    protected function addColumn(Blueprint $table, $field): void
    {
        $column = null;
        
        switch ($field->type) {
            case 'string':
                $column = $table->string($field->columnName, $field->length ?? 255);
                break;
            case 'text':
                $column = $table->text($field->columnName);
                break;
            case 'integer':
            case 'int':
                $column = $table->integer($field->columnName);
                break;
            case 'bigint':
                $column = $table->bigInteger($field->columnName);
                break;
            case 'boolean':
            case 'bool':
                $column = $table->boolean($field->columnName);
                break;
            case 'float':
                $column = $table->float($field->columnName);
                break;
            case 'decimal':
                $column = $table->decimal($field->columnName, $field->precision ?? 10, $field->scale ?? 2);
                break;
            case 'datetime':
                $column = $table->dateTime($field->columnName);
                break;
            case 'date':
                $column = $table->date($field->columnName);
                break;
            case 'time':
                $column = $table->time($field->columnName);
                break;
            case 'timestamp':
                $column = $table->timestamp($field->columnName);
                break;
            case 'json':
                $column = $table->json($field->columnName);
                break;
            case 'binary':
                $column = $table->binary($field->columnName);
                break;
            default:
                $column = $table->string($field->columnName);
        }
        
        if ($field->isId) {
            $column = $table->bigIncrements($field->columnName);
        }
        
        if ($field->isNullable && !$field->isId) {
            $column->nullable();
        }
        
        if ($field->defaultValue !== null && !$field->isId) {
            $column->default($field->defaultValue);
        }
        
        if ($field->isUnique && !$field->isId) {
            $column->unique();
        }
        
        if ($field->comment) {
            $column->comment($field->comment);
        }
    }
    
    protected function buildIndexes(Blueprint $table, EntityMetadata $metadata): void
    {
        foreach ($metadata->fields as $field) {
            if ($field->isTenantId) {
                $table->index($field->columnName);
            }
        }
        
        foreach ($metadata->associations as $association) {
            if ($association->isOwningSide && in_array($association->type, [
                AssociationMetadata::MANY_TO_ONE,
                AssociationMetadata::ONE_TO_ONE
            ])) {
                $joinColumn = $association->getJoinColumnName();
                $table->index($joinColumn);
            }
        }
    }
    
    protected function buildForeignKeys(Blueprint $table, EntityMetadata $metadata): void
    {
        foreach ($metadata->associations as $association) {
            if ($association->isOwningSide && $association->type === AssociationMetadata::MANY_TO_ONE) {
                $targetMetadata = $this->metadataFactory->getMetadata($association->targetEntity);
                $joinColumn = $association->getJoinColumnName();
                $referencedColumn = $association->joinColumn['referencedColumnName'] ?? 'id';
                
                $foreignKey = $table->foreign($joinColumn)
                    ->references($referencedColumn)
                    ->on($targetMetadata->getFullTableName());
                
                if (isset($association->joinColumn['onDelete'])) {
                    $foreignKey->onDelete($association->joinColumn['onDelete']);
                }
                
                if (isset($association->joinColumn['onUpdate'])) {
                    $foreignKey->onUpdate($association->joinColumn['onUpdate']);
                }
            }
        }
    }
    
    public function createJoinTable(EntityMetadata $sourceMetadata, EntityMetadata $targetMetadata, AssociationMetadata $association): void
    {
        $joinTableName = $association->getJoinTableName($sourceMetadata->tableName, $targetMetadata->tableName);
        
        if (Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($joinTableName)) {
            return;
        }
        
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->create($joinTableName, function (Blueprint $table) use ($sourceMetadata, $targetMetadata, $association) {
            $sourceJoinColumn = $association->joinTable['joinColumns'][0]['name'] ?? $sourceMetadata->tableName . '_id';
            $targetJoinColumn = $association->joinTable['inverseJoinColumns'][0]['name'] ?? $targetMetadata->tableName . '_id';
            
            $table->bigInteger($sourceJoinColumn)->unsigned();
            $table->bigInteger($targetJoinColumn)->unsigned();
            
            $table->primary([$sourceJoinColumn, $targetJoinColumn]);
            
            $table->foreign($sourceJoinColumn)
                ->references($sourceMetadata->idField->columnName)
                ->on($sourceMetadata->getFullTableName())
                ->onDelete('cascade');
            
            $table->foreign($targetJoinColumn)
                ->references($targetMetadata->idField->columnName)
                ->on($targetMetadata->getFullTableName())
                ->onDelete('cascade');
        });
    }
    
    public function getTableSchema(string $tableName): array
    {
        $columns = [];
        
        if (Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($tableName)) {
            $columns = Schema::connection($this->entityManager->getConfig()->getConnectionName())->getColumnListing($tableName);
        }
        
        return $columns;
    }
    
    public function tableExists(string $tableName): bool
    {
        return Schema::connection($this->entityManager->getConfig()->getConnectionName())->hasTable($tableName);
    }
    
    public function createSchema(): void
    {
        $allMetadata = $this->metadataFactory->getAllMetadata();
        
        foreach ($allMetadata as $metadata) {
            if (!$metadata->isTenantAware) {
                $this->createTable($metadata);
            }
        }
        
        foreach ($allMetadata as $metadata) {
            foreach ($metadata->associations as $association) {
                if ($association->type === AssociationMetadata::MANY_TO_MANY && $association->isOwningSide) {
                    $targetMetadata = $this->metadataFactory->getMetadata($association->targetEntity);
                    $this->createJoinTable($metadata, $targetMetadata, $association);
                }
            }
        }
    }
    
    public function dropSchema(): void
    {
        $allMetadata = array_reverse($this->metadataFactory->getAllMetadata());
        
        foreach ($allMetadata as $metadata) {
            if (!$metadata->isTenantAware) {
                $this->dropTable($metadata);
            }
        }
    }
    
    public function addColumnToTable(string $tableName, callable $callback): void
    {
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->table($tableName, $callback);
    }
    
    public function renameTable(string $oldName, string $newName): void
    {
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->rename($oldName, $newName);
    }
    
    public function dropColumnFromTable(string $tableName, string $columnName): void
    {
        Schema::connection($this->entityManager->getConfig()->getConnectionName())->table($tableName, function (Blueprint $table) use ($columnName) {
            $table->dropColumn($columnName);
        });
    }
}

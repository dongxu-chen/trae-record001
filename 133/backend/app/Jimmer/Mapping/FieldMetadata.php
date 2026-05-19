<?php

namespace App\Jimmer\Mapping;

class FieldMetadata
{
    public $name;
    public $columnName;
    public $type;
    public $length;
    public $isNullable = false;
    public $isId = false;
    public $isGeneratedValue = false;
    public $generatedStrategy = 'auto';
    public $isUnique = false;
    public $defaultValue;
    public $isVersion = false;
    public $isEncrypted = false;
    public $encryptionAlgorithm = 'AES-256-CBC';
    public $isTenantId = false;
    public $columnDefinition;
    public $comment;
    
    public $precision;
    public $scale;
    
    public function __construct(string $name, string $type)
    {
        $this->name = $name;
        $this->type = $type;
        $this->columnName = $this->toSnakeCase($name);
    }
    
    protected function toSnakeCase(string $str): string
    {
        return strtolower(preg_replace('/(?<!^)[A-Z]/', '_$0', $str));
    }
    
    public function setColumnName(string $columnName): self
    {
        $this->columnName = $columnName;
        return $this;
    }
    
    public function setType(string $type): self
    {
        $this->type = $type;
        return $this;
    }
    
    public function setLength(?int $length): self
    {
        $this->length = $length;
        return $this;
    }
    
    public function setNullable(bool $nullable = true): self
    {
        $this->isNullable = $nullable;
        return $this;
    }
    
    public function setId(bool $isId = true): self
    {
        $this->isId = $isId;
        return $this;
    }
    
    public function setGeneratedValue(bool $generated = true, string $strategy = 'auto'): self
    {
        $this->isGeneratedValue = $generated;
        $this->generatedStrategy = $strategy;
        return $this;
    }
    
    public function setUnique(bool $unique = true): self
    {
        $this->isUnique = $unique;
        return $this;
    }
    
    public function setDefaultValue($value): self
    {
        $this->defaultValue = $value;
        return $this;
    }
    
    public function setVersion(bool $version = true): self
    {
        $this->isVersion = $version;
        return $this;
    }
    
    public function setEncrypted(bool $encrypted = true, string $algorithm = 'AES-256-CBC'): self
    {
        $this->isEncrypted = $encrypted;
        $this->encryptionAlgorithm = $algorithm;
        return $this;
    }
    
    public function setTenantId(bool $tenantId = true): self
    {
        $this->isTenantId = $tenantId;
        return $this;
    }
    
    public function setPrecision(?int $precision): self
    {
        $this->precision = $precision;
        return $this;
    }
    
    public function setScale(?int $scale): self
    {
        $this->scale = $scale;
        return $this;
    }
    
    public function setColumnDefinition(?string $definition): self
    {
        $this->columnDefinition = $definition;
        return $this;
    }
    
    public function setComment(?string $comment): self
    {
        $this->comment = $comment;
        return $this;
    }
    
    public function getPhpType(): string
    {
        $typeMap = [
            'string' => 'string',
            'text' => 'string',
            'integer' => 'int',
            'int' => 'int',
            'boolean' => 'bool',
            'bool' => 'bool',
            'float' => 'float',
            'decimal' => 'float',
            'datetime' => '\DateTimeInterface',
            'date' => '\DateTimeInterface',
            'time' => '\DateTimeInterface',
            'timestamp' => '\DateTimeInterface',
            'array' => 'array',
            'json' => 'array',
            'object' => 'object',
        ];
        
        return $typeMap[$this->type] ?? 'mixed';
    }
    
    public function getSqlDefinition(): string
    {
        if ($this->columnDefinition) {
            return $this->columnDefinition;
        }
        
        $sql = "`{$this->columnName}` ";
        
        switch ($this->type) {
            case 'string':
                $sql .= 'VARCHAR(' . ($this->length ?? 255) . ')';
                break;
            case 'text':
                $sql .= 'TEXT';
                break;
            case 'integer':
            case 'int':
                $sql .= 'INT';
                break;
            case 'bigint':
                $sql .= 'BIGINT';
                break;
            case 'boolean':
            case 'bool':
                $sql .= 'TINYINT(1)';
                break;
            case 'float':
                $sql .= 'FLOAT';
                break;
            case 'decimal':
                $sql .= 'DECIMAL(' . ($this->precision ?? 10) . ',' . ($this->scale ?? 2) . ')';
                break;
            case 'datetime':
                $sql .= 'DATETIME';
                break;
            case 'date':
                $sql .= 'DATE';
                break;
            case 'time':
                $sql .= 'TIME';
                break;
            case 'timestamp':
                $sql .= 'TIMESTAMP';
                break;
            case 'json':
                $sql .= 'JSON';
                break;
            case 'binary':
                $sql .= 'BLOB';
                break;
            default:
                $sql .= strtoupper($this->type);
        }
        
        if ($this->isId) {
            $sql .= ' PRIMARY KEY';
            if ($this->isGeneratedValue && $this->generatedStrategy === 'auto') {
                $sql .= ' AUTO_INCREMENT';
            }
        } else {
            if (!$this->isNullable) {
                $sql .= ' NOT NULL';
            }
            if ($this->defaultValue !== null) {
                if (is_bool($this->defaultValue)) {
                    $sql .= " DEFAULT " . ($this->defaultValue ? 1 : 0);
                } elseif (is_numeric($this->defaultValue)) {
                    $sql .= " DEFAULT {$this->defaultValue}";
                } else {
                    $sql .= " DEFAULT '{$this->defaultValue}'";
                }
            }
            if ($this->isUnique) {
                $sql .= ' UNIQUE';
            }
        }
        
        return $sql;
    }
    
    public static function create(string $name, string $type): self
    {
        return new self($name, $type);
    }
}

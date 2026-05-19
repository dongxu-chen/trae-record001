<?php

namespace App\Jimmer;

use App\Jimmer\Mapping\EntityMetadata;
use App\Jimmer\Mapping\FieldMetadata;
use App\Jimmer\Mapping\AssociationMetadata;
use ReflectionClass;

class MetadataFactory
{
    protected $config;
    protected $metadata = [];
    protected $entityPaths = [];
    
    public function __construct(JimmerConfig $config)
    {
        $this->config = $config;
        $this->entityPaths = $config->getEntityPaths();
        $this->loadMetadata();
    }
    
    protected function loadMetadata(): void
    {
        foreach ($this->entityPaths as $pathConfig) {
            $this->loadFromPath($pathConfig['path'], $pathConfig['namespace']);
        }
    }
    
    protected function loadFromPath(string $path, string $namespace): void
    {
        if (!is_dir($path)) {
            return;
        }
        
        $files = glob($path . '/*.php');
        
        foreach ($files as $file) {
            $className = $namespace . '\\' . pathinfo($file, PATHINFO_FILENAME);
            
            if (class_exists($className)) {
                $this->loadClassMetadata($className);
            }
        }
    }
    
    protected function loadClassMetadata(string $className): void
    {
        if (isset($this->metadata[$className])) {
            return;
        }
        
        $reflection = new ReflectionClass($className);
        
        if (!$reflection->implementsInterface('App\Jimmer\Entity\EntityInterface')) {
            return;
        }
        
        $metadata = new EntityMetadata($className);
        
        $this->parseTableAnnotation($reflection, $metadata);
        $this->parseEntityAnnotations($reflection, $metadata);
        $this->parsePropertyAnnotations($reflection, $metadata);
        
        $this->metadata[$className] = $metadata;
    }
    
    protected function parseTableAnnotation(ReflectionClass $reflection, EntityMetadata $metadata): void
    {
        $docComment = $reflection->getDocComment();
        
        if (preg_match('/@Table\(name="([^"]+)"\)/', $docComment, $matches)) {
            $metadata->tableName = $matches[1];
        } else {
            $shortName = $reflection->getShortName();
            $metadata->tableName = strtolower(preg_replace('/(?<!^)[A-Z]/', '_$0', $shortName)) . 's';
        }
        
        if (preg_match('/@TenantAware/', $docComment)) {
            $metadata->isTenantAware = true;
        }
        
        if (preg_match('/@Repository\(([^)]+)\)/', $docComment, $matches)) {
            $metadata->repositoryClass = trim($matches[1]);
        }
    }
    
    protected function parseEntityAnnotations(ReflectionClass $reflection, EntityMetadata $metadata): void
    {
    }
    
    protected function parsePropertyAnnotations(ReflectionClass $reflection, EntityMetadata $metadata): void
    {
        foreach ($reflection->getProperties() as $property) {
            $docComment = $property->getDocComment();
            $propertyName = $property->getName();
            
            if (preg_match('/@Id/', $docComment)) {
                $field = FieldMetadata::create($propertyName, 'bigint')
                    ->setId()
                    ->setGeneratedValue();
                $metadata->addField($field);
                continue;
            }
            
            if (preg_match('/@Column\(([^)]+)\)/', $docComment, $matches)) {
                $columnConfig = $this->parseAnnotationParams($matches[1]);
                $type = $columnConfig['type'] ?? 'string';
                
                $field = FieldMetadata::create($propertyName, $type);
                
                if (isset($columnConfig['name'])) {
                    $field->setColumnName($columnConfig['name']);
                }
                if (isset($columnConfig['length'])) {
                    $field->setLength((int)$columnConfig['length']);
                }
                if (isset($columnConfig['nullable']) && $columnConfig['nullable'] === 'true') {
                    $field->setNullable();
                }
                if (isset($columnConfig['unique']) && $columnConfig['unique'] === 'true') {
                    $field->setUnique();
                }
                if (isset($columnConfig['default'])) {
                    $field->setDefaultValue($columnConfig['default']);
                }
                
                if (preg_match('/@Encrypted/', $docComment)) {
                    $field->setEncrypted();
                }
                
                if (preg_match('/@TenantId/', $docComment)) {
                    $field->setTenantId();
                }
                
                $metadata->addField($field);
                continue;
            }
            
            if (preg_match('/@OneToOne\(([^)]+)\)/', $docComment, $matches)) {
                $assocConfig = $this->parseAnnotationParams($matches[1]);
                $association = AssociationMetadata::createOneToOne($propertyName);
                
                if (isset($assocConfig['targetEntity'])) {
                    $association->setTargetEntity($assocConfig['targetEntity']);
                }
                if (isset($assocConfig['mappedBy'])) {
                    $association->setMappedBy($assocConfig['mappedBy']);
                }
                if (isset($assocConfig['inversedBy'])) {
                    $association->setInversedBy($assocConfig['inversedBy']);
                }
                if (isset($assocConfig['fetch'])) {
                    $association->setFetchStrategy($assocConfig['fetch']);
                }
                
                if (preg_match('/@JoinColumn\(([^)]+)\)/', $docComment, $joinMatches)) {
                    $association->setJoinColumn($this->parseAnnotationParams($joinMatches[1]));
                }
                
                $metadata->addAssociation($association);
                continue;
            }
            
            if (preg_match('/@OneToMany\(([^)]+)\)/', $docComment, $matches)) {
                $assocConfig = $this->parseAnnotationParams($matches[1]);
                $association = AssociationMetadata::createOneToMany($propertyName);
                
                if (isset($assocConfig['targetEntity'])) {
                    $association->setTargetEntity($assocConfig['targetEntity']);
                }
                if (isset($assocConfig['mappedBy'])) {
                    $association->setMappedBy($assocConfig['mappedBy']);
                }
                if (isset($assocConfig['fetch'])) {
                    $association->setFetchStrategy($assocConfig['fetch']);
                }
                if (isset($assocConfig['orphanRemoval']) && $assocConfig['orphanRemoval'] === 'true') {
                    $association->setOrphanRemoval(true);
                }
                
                $metadata->addAssociation($association);
                continue;
            }
            
            if (preg_match('/@ManyToOne\(([^)]+)\)/', $docComment, $matches)) {
                $assocConfig = $this->parseAnnotationParams($matches[1]);
                $association = AssociationMetadata::createManyToOne($propertyName);
                
                if (isset($assocConfig['targetEntity'])) {
                    $association->setTargetEntity($assocConfig['targetEntity']);
                }
                if (isset($assocConfig['inversedBy'])) {
                    $association->setInversedBy($assocConfig['inversedBy']);
                }
                if (isset($assocConfig['fetch'])) {
                    $association->setFetchStrategy($assocConfig['fetch']);
                }
                
                if (preg_match('/@JoinColumn\(([^)]+)\)/', $docComment, $joinMatches)) {
                    $association->setJoinColumn($this->parseAnnotationParams($joinMatches[1]));
                }
                
                $metadata->addAssociation($association);
                continue;
            }
            
            if (preg_match('/@ManyToMany\(([^)]+)\)/', $docComment, $matches)) {
                $assocConfig = $this->parseAnnotationParams($matches[1]);
                $association = AssociationMetadata::createManyToMany($propertyName);
                
                if (isset($assocConfig['targetEntity'])) {
                    $association->setTargetEntity($assocConfig['targetEntity']);
                }
                if (isset($assocConfig['mappedBy'])) {
                    $association->setMappedBy($assocConfig['mappedBy']);
                }
                if (isset($assocConfig['inversedBy'])) {
                    $association->setInversedBy($assocConfig['inversedBy']);
                }
                if (isset($assocConfig['fetch'])) {
                    $association->setFetchStrategy($assocConfig['fetch']);
                }
                
                if (preg_match('/@JoinTable\(([^)]+)\)/', $docComment, $joinMatches)) {
                    $association->setJoinTable($this->parseAnnotationParams($joinMatches[1]));
                }
                
                $metadata->addAssociation($association);
                continue;
            }
        }
    }
    
    protected function parseAnnotationParams(string $params): array
    {
        $result = [];
        
        if (preg_match_all('/(\w+)="([^"]+)"/', $params, $matches, PREG_SET_ORDER)) {
            foreach ($matches as $match) {
                $result[$match[1]] = $match[2];
            }
        }
        
        return $result;
    }
    
    public function getMetadata(string $className): EntityMetadata
    {
        if (!isset($this->metadata[$className])) {
            $this->loadClassMetadata($className);
        }
        
        if (!isset($this->metadata[$className])) {
            throw new \RuntimeException("No metadata found for class: {$className}");
        }
        
        return $this->metadata[$className];
    }
    
    public function hasMetadata(string $className): bool
    {
        return isset($this->metadata[$className]);
    }
    
    public function getAllMetadata(): array
    {
        return $this->metadata;
    }
    
    public function registerMetadata(EntityMetadata $metadata): void
    {
        $this->metadata[$metadata->className] = $metadata;
    }
    
    public function clearCache(): void
    {
        $this->metadata = [];
    }
}

<?php

namespace App\Jimmer\Entity;

use App\Jimmer\Entity\EntityInterface;

/**
 * @Table(name="forms")
 * @TenantAware
 * @RepositoryClass("App\Repository\FormRepository")
 */
class Form implements EntityInterface
{
    /**
     * @Id
     * @GeneratedValue
     * @Column(type="bigint")
     */
    protected $id;
    
    /**
     * @Column(type="string", length=255)
     */
    protected $name;
    
    /**
     * @Column(type="text", nullable=true)
     * @Encrypted
     */
    protected $description;
    
    /**
     * @Column(type="json", nullable=true)
     */
    protected $schema;
    
    /**
     * @Column(type="boolean")
     */
    protected $isActive = true;
    
    /**
     * @Column(type="string", length=100)
     * @TenantId
     */
    protected $tenantId;
    
    /**
     * @Column(type="datetime")
     */
    protected $createdAt;
    
    /**
     * @Column(type="datetime")
     */
    protected $updatedAt;
    
    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
        $this->updatedAt = new \DateTimeImmutable();
    }
    
    public function getId()
    {
        return $this->id;
    }
    
    public function setId($id): self
    {
        $this->id = $id;
        return $this;
    }
    
    public function getName(): ?string
    {
        return $this->name;
    }
    
    public function setName(string $name): self
    {
        $this->name = $name;
        return $this;
    }
    
    public function getDescription(): ?string
    {
        return $this->description;
    }
    
    public function setDescription(?string $description): self
    {
        $this->description = $description;
        return $this;
    }
    
    public function getSchema(): ?array
    {
        return $this->schema;
    }
    
    public function setSchema(?array $schema): self
    {
        $this->schema = $schema;
        return $this;
    }
    
    public function isActive(): bool
    {
        return $this->isActive;
    }
    
    public function setIsActive(bool $isActive): self
    {
        $this->isActive = $isActive;
        return $this;
    }
    
    public function getTenantId(): ?string
    {
        return $this->tenantId;
    }
    
    public function setTenantId(string $tenantId): self
    {
        $this->tenantId = $tenantId;
        return $this;
    }
    
    public function getCreatedAt(): ?\DateTimeInterface
    {
        return $this->createdAt;
    }
    
    public function setCreatedAt(\DateTimeInterface $createdAt): self
    {
        $this->createdAt = $createdAt;
        return $this;
    }
    
    public function getUpdatedAt(): ?\DateTimeInterface
    {
        return $this->updatedAt;
    }
    
    public function setUpdatedAt(\DateTimeInterface $updatedAt): self
    {
        $this->updatedAt = $updatedAt;
        return $this;
    }
}

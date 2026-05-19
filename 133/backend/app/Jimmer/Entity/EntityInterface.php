<?php

namespace App\Jimmer\Entity;

interface EntityInterface
{
    public function getId();
    public function setId($id): self;
}

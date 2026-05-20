<?php

namespace App\Jimmer\Encryption;

class EncryptionManager
{
    protected $config;
    protected $key;
    protected $cipher;
    protected $enabled;
    
    public function __construct(\App\Jimmer\JimmerConfig $config)
    {
        $this->config = $config;
        $this->key = $config->getEncryptionKey();
        $this->cipher = 'AES-256-CBC';
        $this->enabled = $config->isEncryptionEnabled();
    }
    
    public function encrypt($value): ?string
    {
        if (!$this->enabled || $value === null) {
            return $value;
        }
        
        $iv = random_bytes(openssl_cipher_iv_length($this->cipher));
        $encrypted = openssl_encrypt(
            $this->serializeValue($value),
            $this->cipher,
            $this->getEncryptionKey(),
            0,
            $iv
        );
        
        if ($encrypted === false) {
            throw new \RuntimeException('Encryption failed.');
        }
        
        $hmac = hash_hmac('sha256', $iv . $encrypted, $this->getEncryptionKey());
        
        return base64_encode(json_encode([
            'iv' => base64_encode($iv),
            'value' => $encrypted,
            'hmac' => $hmac,
            'type' => gettype($value),
        ]));
    }
    
    public function decrypt(?string $payload)
    {
        if (!$this->enabled || $payload === null) {
            return $payload;
        }
        
        try {
            $data = json_decode(base64_decode($payload), true);
            
            if (!$this->isValidPayload($data)) {
                throw new \RuntimeException('Invalid encryption payload.');
            }
            
            $iv = base64_decode($data['iv']);
            
            $calculatedHmac = hash_hmac('sha256', $iv . $data['value'], $this->getEncryptionKey());
            
            if (!hash_equals($calculatedHmac, $data['hmac'])) {
                throw new \RuntimeException('HMAC verification failed.');
            }
            
            $decrypted = openssl_decrypt(
                $data['value'],
                $this->cipher,
                $this->getEncryptionKey(),
                0,
                $iv
            );
            
            if ($decrypted === false) {
                throw new \RuntimeException('Decryption failed.');
            }
            
            return $this->unserializeValue($decrypted, $data['type'] ?? 'string');
        } catch (\Exception $e) {
            throw new \RuntimeException('Decryption failed: ' . $e->getMessage());
        }
    }
    
    protected function serializeValue($value): string
    {
        if (is_bool($value)) {
            return $value ? '1' : '0';
        }
        
        if (is_numeric($value)) {
            return (string)$value;
        }
        
        if (is_array($value) || is_object($value)) {
            return json_encode($value);
        }
        
        return (string)$value;
    }
    
    protected function unserializeValue(string $value, string $type)
    {
        switch ($type) {
            case 'boolean':
            case 'bool':
                return $value === '1';
            case 'integer':
            case 'int':
                return (int)$value;
            case 'float':
            case 'double':
                return (float)$value;
            case 'array':
                return json_decode($value, true);
            case 'object':
                return json_decode($value);
            default:
                return $value;
        }
    }
    
    protected function isValidPayload($data): bool
    {
        return is_array($data) &&
            isset($data['iv'], $data['value'], $data['hmac']) &&
            base64_decode($data['iv'], true) !== false;
    }
    
    protected function getEncryptionKey(): string
    {
        if (empty($this->key)) {
            throw new \RuntimeException('No encryption key specified.');
        }
        
        if (strpos($this->key, 'base64:') === 0) {
            return base64_decode(substr($this->key, 7));
        }
        
        return $this->key;
    }
    
    public function isEnabled(): bool
    {
        return $this->enabled;
    }
    
    public function setEnabled(bool $enabled): self
    {
        $this->enabled = $enabled;
        return $this;
    }
    
    public static function generateKey(): string
    {
        return 'base64:' . base64_encode(random_bytes(32));
    }
}

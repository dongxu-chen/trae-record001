package config

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

type RegistryType string

const (
	RegistryTypeHarbor RegistryType = "harbor"
	RegistryTypeACR    RegistryType = "acr"
	RegistryTypeECR    RegistryType = "ecr"
	RegistryTypeGeneric RegistryType = "generic"
)

type RegistryConfig struct {
	Name      string       `json:"name"`
	Type      RegistryType `json:"type"`
	URL       string       `json:"url"`
	Username  string       `json:"username,omitempty"`
	Password  string       `json:"password,omitempty"`
	AccessKey string       `json:"access_key,omitempty"`
	SecretKey string       `json:"secret_key,omitempty"`
	Region    string       `json:"region,omitempty"`
	Insecure  bool         `json:"insecure,omitempty"`
}

type RelayNodeConfig struct {
	Name     string       `json:"name"`
	Type     RegistryType `json:"type"`
	URL      string       `json:"url"`
	Username string       `json:"username,omitempty"`
	Password string       `json:"password,omitempty"`
	Region   string       `json:"region"`
	Insecure bool         `json:"insecure,omitempty"`
}

type CleanupConfig struct {
	Enabled          bool   `json:"enabled"`
	DeleteTags       bool   `json:"delete_tags"`
	DeleteManifests  bool   `json:"delete_manifests"`
	DryRun           bool   `json:"dry_run,omitempty"`
	RetentionDays    int    `json:"retention_days,omitempty"`
}

type AuditConfig struct {
	Enabled  bool   `json:"enabled"`
	LogPath  string `json:"log_path"`
	Operator string `json:"operator"`
	BatchSize int   `json:"batch_size,omitempty"`
}

type FilterConfig struct {
	IncludeNamespaces []string `json:"include_namespaces,omitempty"`
	ExcludeNamespaces []string `json:"exclude_namespaces,omitempty"`
	IncludeTags       []string `json:"include_tags,omitempty"`
	ExcludeTags       []string `json:"exclude_tags,omitempty"`
}

type RateLimitConfig struct {
	MaxConcurrent int   `json:"max_concurrent"`
	BytesPerSec   int64 `json:"bytes_per_sec,omitempty"`
}

type SyncConfig struct {
	SourceRegistry string            `json:"source_registry"`
	TargetRegistry string            `json:"target_registry"`
	SourcePrefix   string            `json:"source_prefix,omitempty"`
	TargetPrefix   string            `json:"target_prefix,omitempty"`
	RelayNodes     []RelayNodeConfig `json:"relay_nodes,omitempty"`
	Filter         FilterConfig      `json:"filter"`
	RateLimit      RateLimitConfig   `json:"rate_limit"`
	Incremental    bool              `json:"incremental"`
	VerifyDigest   bool              `json:"verify_digest"`
	DryRun         bool              `json:"dry_run,omitempty"`
	Cleanup        CleanupConfig     `json:"cleanup,omitempty"`
	Audit          AuditConfig       `json:"audit,omitempty"`
}

type Config struct {
	Registries []RegistryConfig `json:"registries"`
	SyncJobs   []SyncConfig     `json:"sync_jobs"`
	Encrypted  bool             `json:"encrypted,omitempty"`
}

type EncryptionManager struct {
	key []byte
}

func NewEncryptionManager(key string) *EncryptionManager {
	keyBytes := []byte(key)
	if len(keyBytes) < 32 {
		padded := make([]byte, 32)
		copy(padded, keyBytes)
		keyBytes = padded
	} else if len(keyBytes) > 32 {
		keyBytes = keyBytes[:32]
	}
	return &EncryptionManager{key: keyBytes}
}

func (em *EncryptionManager) Encrypt(plaintext string) (string, error) {
	block, err := aes.NewCipher(em.key)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}

	ciphertext := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	return base64.StdEncoding.EncodeToString(ciphertext), nil
}

func (em *EncryptionManager) Decrypt(ciphertext string) (string, error) {
	data, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(em.key)
	if err != nil {
		return "", err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return "", fmt.Errorf("ciphertext too short")
	}

	nonce, ciphertextBytes := data[:nonceSize], data[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertextBytes, nil)
	if err != nil {
		return "", err
	}

	return string(plaintext), nil
}

func (em *EncryptionManager) EncryptConfig(cfg *Config) error {
	for i := range cfg.Registries {
		reg := &cfg.Registries[i]
		if reg.Password != "" && !strings.HasPrefix(reg.Password, "ENC:") {
			enc, err := em.Encrypt(reg.Password)
			if err != nil {
				return err
			}
			reg.Password = "ENC:" + enc
		}
		if reg.SecretKey != "" && !strings.HasPrefix(reg.SecretKey, "ENC:") {
			enc, err := em.Encrypt(reg.SecretKey)
			if err != nil {
				return err
			}
			reg.SecretKey = "ENC:" + enc
		}
	}
	cfg.Encrypted = true
	return nil
}

func (em *EncryptionManager) DecryptConfig(cfg *Config) error {
	for i := range cfg.Registries {
		reg := &cfg.Registries[i]
		if strings.HasPrefix(reg.Password, "ENC:") {
			dec, err := em.Decrypt(strings.TrimPrefix(reg.Password, "ENC:"))
			if err != nil {
				return err
			}
			reg.Password = dec
		}
		if strings.HasPrefix(reg.SecretKey, "ENC:") {
			dec, err := em.Decrypt(strings.TrimPrefix(reg.SecretKey, "ENC:"))
			if err != nil {
				return err
			}
			reg.SecretKey = dec
		}
	}
	return nil
}

func LoadConfig(path string, encryptionKey string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	if cfg.Encrypted && encryptionKey != "" {
		em := NewEncryptionManager(encryptionKey)
		if err := em.DecryptConfig(&cfg); err != nil {
			return nil, fmt.Errorf("failed to decrypt config: %w", err)
		}
	}

	return &cfg, nil
}

func SaveConfig(path string, cfg *Config, encryptionKey string) error {
	if encryptionKey != "" {
		em := NewEncryptionManager(encryptionKey)
		if err := em.EncryptConfig(cfg); err != nil {
			return err
		}
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(path, data, 0600)
}

func (c *Config) GetRegistry(name string) (*RegistryConfig, bool) {
	for i := range c.Registries {
		if c.Registries[i].Name == name {
			return &c.Registries[i], true
		}
	}
	return nil, false
}

package encryption

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

type KMSProvider interface {
	Encrypt(dataKey []byte, keyID string) ([]byte, error)
	Decrypt(encryptedKey []byte, keyID string) ([]byte, error)
	GetCurrentKeyID() string
	RotateKey() (string, error)
	HealthCheck() error
}

type LocalKMSProvider struct {
	keys       map[string][]byte
	activeKey  string
	mu         sync.RWMutex
	keyDir     string
}

func NewLocalKMSProvider(keyDir string) (*LocalKMSProvider, error) {
	if err := os.MkdirAll(keyDir, 0700); err != nil {
		return nil, fmt.Errorf("failed to create key directory: %w", err)
	}

	p := &LocalKMSProvider{
		keys:   make(map[string][]byte),
		keyDir: keyDir,
	}

	if err := p.loadKeys(); err != nil {
		return nil, err
	}

	if len(p.keys) == 0 {
		if _, err := p.RotateKey(); err != nil {
			return nil, err
		}
	}

	return p, nil
}

func (p *LocalKMSProvider) loadKeys() error {
	entries, err := os.ReadDir(p.keyDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("failed to read key directory: %w", err)
	}

	var latestKey string
	var latestTime time.Time

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".key") {
			continue
		}

		keyPath := fmt.Sprintf("%s/%s", p.keyDir, entry.Name())
		keyData, err := os.ReadFile(keyPath)
		if err != nil {
			continue
		}

		keyID := strings.TrimSuffix(entry.Name(), ".key")
		keyBytes, err := base64.StdEncoding.DecodeString(string(keyData))
		if err != nil {
			continue
		}

		if len(keyBytes) == keySize {
			p.keys[keyID] = keyBytes

			info, _ := entry.Info()
			if info != nil && info.ModTime().After(latestTime) {
				latestTime = info.ModTime()
				latestKey = keyID
			}
		}
	}

	if latestKey != "" {
		p.activeKey = latestKey
	}

	return nil
}

func (p *LocalKMSProvider) Encrypt(dataKey []byte, keyID string) ([]byte, error) {
	p.mu.RLock()
	masterKey, exists := p.keys[keyID]
	p.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("key %s not found", keyID)
	}

	block, err := aes.NewCipher(masterKey)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}

	return gcm.Seal(nonce, nonce, dataKey, nil), nil
}

func (p *LocalKMSProvider) Decrypt(encryptedKey []byte, keyID string) ([]byte, error) {
	p.mu.RLock()
	masterKey, exists := p.keys[keyID]
	p.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("key %s not found", keyID)
	}

	block, err := aes.NewCipher(masterKey)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonceSize := gcm.NonceSize()
	if len(encryptedKey) < nonceSize {
		return nil, fmt.Errorf("encrypted key too short")
	}

	nonce, ciphertext := encryptedKey[:nonceSize], encryptedKey[nonceSize:]
	return gcm.Open(nil, nonce, ciphertext, nil)
}

func (p *LocalKMSProvider) GetCurrentKeyID() string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.activeKey
}

func (p *LocalKMSProvider) RotateKey() (string, error) {
	key := make([]byte, keySize)
	if _, err := rand.Read(key); err != nil {
		return "", fmt.Errorf("failed to generate key: %w", err)
	}

	keyID := fmt.Sprintf("key-%d", time.Now().UnixNano())
	encoded := base64.StdEncoding.EncodeToString(key)

	keyPath := fmt.Sprintf("%s/%s.key", p.keyDir, keyID)
	if err := os.WriteFile(keyPath, []byte(encoded), 0600); err != nil {
		return "", fmt.Errorf("failed to write key file: %w", err)
	}

	p.mu.Lock()
	p.keys[keyID] = key
	p.activeKey = keyID
	p.mu.Unlock()

	return keyID, nil
}

func (p *LocalKMSProvider) HealthCheck() error {
	p.mu.RLock()
	_, exists := p.keys[p.activeKey]
	p.mu.RUnlock()

	if !exists {
		return fmt.Errorf("no active key available")
	}
	return nil
}

type VaultKMSProvider struct {
	endpoint   string
	token      string
	keyName    string
	keyVersion int
	httpClient *http.Client
}

func NewVaultKMSProvider(endpoint, token, keyName string) *VaultKMSProvider {
	return &VaultKMSProvider{
		endpoint:   strings.TrimRight(endpoint, "/"),
		token:      token,
		keyName:    keyName,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

type vaultEncryptRequest struct {
	Plaintext string `json:"plaintext"`
}

type vaultEncryptResponse struct {
	Data struct {
		Ciphertext string `json:"ciphertext"`
		KeyVersion int    `json:"key_version"`
	} `json:"data"`
}

type vaultDecryptRequest struct {
	Ciphertext string `json:"ciphertext"`
}

type vaultDecryptResponse struct {
	Data struct {
		Plaintext string `json:"plaintext"`
	} `json:"data"`
}

func (v *VaultKMSProvider) Encrypt(dataKey []byte, keyID string) ([]byte, error) {
	plaintext := base64.StdEncoding.EncodeToString(dataKey)

	reqBody := vaultEncryptRequest{Plaintext: plaintext}
	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/v1/transit/encrypt/%s", v.endpoint, v.keyName)
	req, err := http.NewRequest("POST", url, strings.NewReader(string(bodyBytes)))
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-Vault-Token", v.token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("vault encrypt request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("vault encrypt failed with status %d", resp.StatusCode)
	}

	var vaultResp vaultEncryptResponse
	if err := json.NewDecoder(resp.Body).Decode(&vaultResp); err != nil {
		return nil, err
	}

	v.keyVersion = vaultResp.Data.KeyVersion

	return []byte(vaultResp.Data.Ciphertext), nil
}

func (v *VaultKMSProvider) Decrypt(encryptedKey []byte, keyID string) ([]byte, error) {
	reqBody := vaultDecryptRequest{Ciphertext: string(encryptedKey)}
	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, err
	}

	url := fmt.Sprintf("%s/v1/transit/decrypt/%s", v.endpoint, v.keyName)
	req, err := http.NewRequest("POST", url, strings.NewReader(string(bodyBytes)))
	if err != nil {
		return nil, err
	}

	req.Header.Set("X-Vault-Token", v.token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := v.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("vault decrypt request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("vault decrypt failed with status %d", resp.StatusCode)
	}

	var vaultResp vaultDecryptResponse
	if err := json.NewDecoder(resp.Body).Decode(&vaultResp); err != nil {
		return nil, err
	}

	return base64.StdEncoding.DecodeString(vaultResp.Data.Plaintext)
}

func (v *VaultKMSProvider) GetCurrentKeyID() string {
	return fmt.Sprintf("%s/v%d", v.keyName, v.keyVersion)
}

func (v *VaultKMSProvider) RotateKey() (string, error) {
	url := fmt.Sprintf("%s/v1/transit/keys/%s/rotate", v.endpoint, v.keyName)
	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return "", err
	}

	req.Header.Set("X-Vault-Token", v.token)

	resp, err := v.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("vault rotate request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return "", fmt.Errorf("vault rotate failed with status %d", resp.StatusCode)
	}

	v.keyVersion++
	return v.GetCurrentKeyID(), nil
}

func (v *VaultKMSProvider) HealthCheck() error {
	url := fmt.Sprintf("%s/v1/sys/health", v.endpoint)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}

	resp, err := v.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("vault health check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("vault is not healthy: status %d", resp.StatusCode)
	}
	return nil
}

type AWSKMSProvider struct {
	region    string
	keyID     string
	accessKey string
	secretKey string
	client    *http.Client
}

func NewAWSKMSProvider(region, keyID, accessKey, secretKey string) *AWSKMSProvider {
	return &AWSKMSProvider{
		region:    region,
		keyID:     keyID,
		accessKey: accessKey,
		secretKey: secretKey,
		client:    &http.Client{Timeout: 30 * time.Second},
	}
}

func (a *AWSKMSProvider) Encrypt(dataKey []byte, keyID string) ([]byte, error) {
	return nil, fmt.Errorf("AWS KMS requires sigv4 signing; use aws-sdk-go for production")
}

func (a *AWSKMSProvider) Decrypt(encryptedKey []byte, keyID string) ([]byte, error) {
	return nil, fmt.Errorf("AWS KMS requires sigv4 signing; use aws-sdk-go for production")
}

func (a *AWSKMSProvider) GetCurrentKeyID() string {
	return a.keyID
}

func (a *AWSKMSProvider) RotateKey() (string, error) {
	return "", fmt.Errorf("AWS KMS key rotation should be configured in AWS console")
}

func (a *AWSKMSProvider) HealthCheck() error {
	return fmt.Errorf("AWS KMS health check requires sigv4 signing; use aws-sdk-go for production")
}

type KMSEncryptor struct {
	provider  KMSProvider
	dataKeys  map[string]*dataKeyEntry
	mu        sync.RWMutex
	enabled   bool
}

type dataKeyEntry struct {
	Key          []byte
	EncryptedKey []byte
	KeyID        string
	CreatedAt    time.Time
	ExpiresAt    time.Time
}

func NewKMSEncryptor(provider KMSProvider) *KMSEncryptor {
	return &KMSEncryptor{
		provider: provider,
		dataKeys: make(map[string]*dataKeyEntry),
		enabled:  true,
	}
}

func (e *KMSEncryptor) generateDataKey() (*dataKeyEntry, error) {
	dataKey := make([]byte, keySize)
	if _, err := rand.Read(dataKey); err != nil {
		return nil, fmt.Errorf("failed to generate data key: %w", err)
	}

	keyID := e.provider.GetCurrentKeyID()
	encryptedKey, err := e.provider.Encrypt(dataKey, keyID)
	if err != nil {
		return nil, fmt.Errorf("failed to encrypt data key with KMS: %w", err)
	}

	entry := &dataKeyEntry{
		Key:          dataKey,
		EncryptedKey: encryptedKey,
		KeyID:        keyID,
		CreatedAt:    time.Now(),
		ExpiresAt:    time.Now().Add(24 * time.Hour),
	}

	return entry, nil
}

func (e *KMSEncryptor) getDataKey(id string) (*dataKeyEntry, error) {
	e.mu.RLock()
	entry, exists := e.dataKeys[id]
	e.mu.RUnlock()

	if exists && time.Now().Before(entry.ExpiresAt) {
		return entry, nil
	}

	return nil, fmt.Errorf("data key %s not found or expired", id)
}

func (e *KMSEncryptor) Encrypt(data []byte) ([]byte, error) {
	if !e.enabled {
		return data, nil
	}

	entry, err := e.generateDataKey()
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(entry.Key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, err
	}

	ciphertext := gcm.Seal(nonce, nonce, data, nil)

	encKeyLen := len(entry.EncryptedKey)
	result := make([]byte, 4+encKeyLen+len(ciphertext))
	result[0] = byte(encKeyLen >> 24)
	result[1] = byte(encKeyLen >> 16)
	result[2] = byte(encKeyLen >> 8)
	result[3] = byte(encKeyLen)
	copy(result[4:4+encKeyLen], entry.EncryptedKey)
	copy(result[4+encKeyLen:], ciphertext)

	return result, nil
}

func (e *KMSEncryptor) Decrypt(data []byte) ([]byte, error) {
	if !e.enabled {
		return data, nil
	}

	if len(data) < 4 {
		return nil, fmt.Errorf("invalid KMS encrypted data: too short")
	}

	encKeyLen := int(data[0])<<24 | int(data[1])<<16 | int(data[2])<<8 | int(data[3])

	if len(data) < 4+encKeyLen {
		return nil, fmt.Errorf("invalid KMS encrypted data: encrypted key incomplete")
	}

	encryptedKey := data[4 : 4+encKeyLen]
	ciphertext := data[4+encKeyLen:]

	cacheKey := base64.StdEncoding.EncodeToString(encryptedKey)
	entry, err := e.getDataKey(cacheKey)
	if err != nil {
		dataKey, err := e.provider.Decrypt(encryptedKey, "")
		if err != nil {
			return nil, fmt.Errorf("failed to decrypt data key with KMS: %w", err)
		}

		entry = &dataKeyEntry{
			Key:          dataKey,
			EncryptedKey: encryptedKey,
			CreatedAt:    time.Now(),
			ExpiresAt:    time.Now().Add(24 * time.Hour),
		}

		e.mu.Lock()
		e.dataKeys[cacheKey] = entry
		e.mu.Unlock()
	}

	block, err := aes.NewCipher(entry.Key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonceSize := gcm.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}

	nonce, ct := ciphertext[:nonceSize], ciphertext[nonceSize:]
	return gcm.Open(nil, nonce, ct, nil)
}

func (e *KMSEncryptor) IsEnabled() bool {
	return e.enabled
}

func (e *KMSEncryptor) GetCurrentKeyID() string {
	return e.provider.GetCurrentKeyID()
}

func (e *KMSEncryptor) RotateKey() (string, error) {
	return e.provider.RotateKey()
}

func (e *KMSEncryptor) HealthCheck() error {
	return e.provider.HealthCheck()
}

func NewKMSProviderFromConfig(config KMSConfig) (KMSProvider, error) {
	switch config.Provider {
	case "local":
		keyDir := "./data/kms-keys"
		if config.Endpoint != "" {
			keyDir = config.Endpoint
		}
		return NewLocalKMSProvider(keyDir)
	case "vault":
		if config.Endpoint == "" || config.Token == "" || config.KeyID == "" {
			return nil, fmt.Errorf("vault KMS requires endpoint, token, and keyId")
		}
		return NewVaultKMSProvider(config.Endpoint, config.Token, config.KeyID), nil
	case "aws":
		if config.KeyID == "" {
			return nil, fmt.Errorf("AWS KMS requires keyId")
		}
		return NewAWSKMSProvider(config.Region, config.KeyID, config.AccessKey, config.SecretKey), nil
	default:
		return nil, fmt.Errorf("unsupported KMS provider: %s", config.Provider)
	}
}

type KMSConfig struct {
	Provider  string `json:"provider" yaml:"provider"`
	Endpoint  string `json:"endpoint,omitempty" yaml:"endpoint,omitempty"`
	Region    string `json:"region,omitempty" yaml:"region,omitempty"`
	AccessKey string `json:"accessKey,omitempty" yaml:"accessKey,omitempty"`
	SecretKey string `json:"secretKey,omitempty" yaml:"secretKey,omitempty"`
	KeyID     string `json:"keyId,omitempty" yaml:"keyId,omitempty"`
	KeyVault  string `json:"keyVault,omitempty" yaml:"keyVault,omitempty"`
	Token     string `json:"token,omitempty" yaml:"token,omitempty"`
}

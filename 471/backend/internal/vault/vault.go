package vault

import (
	"context"
	"fmt"
	"time"

	"github.com/hashicorp/vault/api"
	"github.com/sirupsen/logrus"
)

type VaultClient struct {
	client *api.Client
	log    *logrus.Logger
	mountPath string
}

type Config struct {
	Address   string
	Token     string
	MountPath string
}

func NewVaultClient(cfg Config, log *logrus.Logger) (*VaultClient, error) {
	config := api.DefaultConfig()
	config.Address = cfg.Address

	client, err := api.NewClient(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create vault client: %w", err)
	}

	client.SetToken(cfg.Token)

	mountPath := cfg.MountPath
	if mountPath == "" {
		mountPath = "secret"
	}

	return &VaultClient{
		client: client,
		log:    log,
		mountPath: mountPath,
	}, nil
}

func (vc *VaultClient) StoreSecret(ctx context.Context, path string, data map[string]interface{}) error {
	secretPath := fmt.Sprintf("%s/data/%s", vc.mountPath, path)
	
	_, err := vc.client.Logical().Write(secretPath, map[string]interface{}{
		"data": data,
	})
	if err != nil {
		vc.log.Errorf("Failed to store secret at %s: %v", path, err)
		return fmt.Errorf("failed to store secret: %w", err)
	}

	vc.log.Infof("Secret stored successfully at %s", path)
	return nil
}

func (vc *VaultClient) GetSecret(ctx context.Context, path string) (map[string]interface{}, error) {
	secretPath := fmt.Sprintf("%s/data/%s", vc.mountPath, path)
	
	secret, err := vc.client.Logical().Read(secretPath)
	if err != nil {
		vc.log.Errorf("Failed to read secret at %s: %v", path, err)
		return nil, fmt.Errorf("failed to read secret: %w", err)
	}

	if secret == nil || secret.Data == nil {
		return nil, fmt.Errorf("secret not found at %s", path)
	}

	data, ok := secret.Data["data"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid secret data format")
	}

	return data, nil
}

func (vc *VaultClient) DeleteSecret(ctx context.Context, path string) error {
	secretPath := fmt.Sprintf("%s/metadata/%s", vc.mountPath, path)
	
	_, err := vc.client.Logical().Delete(secretPath)
	if err != nil {
		vc.log.Errorf("Failed to delete secret at %s: %v", path, err)
		return fmt.Errorf("failed to delete secret: %w", err)
	}

	vc.log.Infof("Secret deleted successfully at %s", path)
	return nil
}

func (vc *VaultClient) RotateSecret(ctx context.Context, path string, newData map[string]interface{}) error {
	if err := vc.StoreSecret(ctx, path, newData); err != nil {
		return fmt.Errorf("failed to rotate secret: %w", err)
	}

	vc.log.Infof("Secret rotated successfully at %s", path)
	return nil
}

func (vc *VaultClient) ListSecrets(ctx context.Context, path string) ([]string, error) {
	listPath := fmt.Sprintf("%s/metadata/%s", vc.mountPath, path)
	
	secret, err := vc.client.Logical().List(listPath)
	if err != nil {
		vc.log.Errorf("Failed to list secrets at %s: %v", path, err)
		return nil, fmt.Errorf("failed to list secrets: %w", err)
	}

	if secret == nil || secret.Data == nil {
		return []string{}, nil
	}

	keys, ok := secret.Data["keys"].([]interface{})
	if !ok {
		return []string{}, nil
	}

	result := make([]string, len(keys))
	for i, key := range keys {
		result[i] = key.(string)
	}

	return result, nil
}

func (vc *VaultClient) Encrypt(ctx context.Context, keyName string, plaintext []byte) (string, error) {
	path := fmt.Sprintf("transit/encrypt/%s", keyName)
	
	secret, err := vc.client.Logical().Write(path, map[string]interface{}{
		"plaintext": plaintext,
	})
	if err != nil {
		vc.log.Errorf("Failed to encrypt with key %s: %v", keyName, err)
		return "", fmt.Errorf("encryption failed: %w", err)
	}

	ciphertext, ok := secret.Data["ciphertext"].(string)
	if !ok {
		return "", fmt.Errorf("invalid ciphertext format")
	}

	return ciphertext, nil
}

func (vc *VaultClient) Decrypt(ctx context.Context, keyName string, ciphertext string) ([]byte, error) {
	path := fmt.Sprintf("transit/decrypt/%s", keyName)
	
	secret, err := vc.client.Logical().Write(path, map[string]interface{}{
		"ciphertext": ciphertext,
	})
	if err != nil {
		vc.log.Errorf("Failed to decrypt with key %s: %v", keyName, err)
		return nil, fmt.Errorf("decryption failed: %w", err)
	}

	plaintext, ok := secret.Data["plaintext"].(string)
	if !ok {
		return nil, fmt.Errorf("invalid plaintext format")
	}

	return []byte(plaintext), nil
}

func (vc *VaultClient) CreateEncryptionKey(ctx context.Context, keyName string) error {
	path := fmt.Sprintf("transit/keys/%s", keyName)
	
	_, err := vc.client.Logical().Write(path, map[string]interface{}{
		"type": "aes256-gcm96",
	})
	if err != nil {
		vc.log.Errorf("Failed to create encryption key %s: %v", keyName, err)
		return fmt.Errorf("failed to create encryption key: %w", err)
	}

	vc.log.Infof("Encryption key created: %s", keyName)
	return nil
}

func (vc *VaultClient) GenerateDatabaseCredentials(ctx context.Context, role string) (map[string]interface{}, error) {
	path := fmt.Sprintf("database/creds/%s", role)
	
	secret, err := vc.client.Logical().Read(path)
	if err != nil {
		vc.log.Errorf("Failed to generate database credentials for role %s: %v", role, err)
		return nil, fmt.Errorf("failed to generate credentials: %w", err)
	}

	if secret == nil || secret.Data == nil {
		return nil, fmt.Errorf("no credentials returned")
	}

	credentials := map[string]interface{}{
		"username": secret.Data["username"],
		"password": secret.Data["password"],
	}

	if leaseID, ok := secret.LeaseID; ok {
		credentials["lease_id"] = leaseID
	}
	if leaseDuration, ok := secret.LeaseDuration; ok {
		credentials["lease_duration"] = leaseDuration
		credentials["expires_at"] = time.Now().Add(time.Duration(leaseDuration) * time.Second)
	}

	return credentials, nil
}

func (vc *VaultClient) HealthCheck(ctx context.Context) error {
	health, err := vc.client.Sys().Health()
	if err != nil {
		return fmt.Errorf("vault health check failed: %w", err)
	}

	if !health.Initialized {
		return fmt.Errorf("vault is not initialized")
	}

	if health.Sealed {
		return fmt.Errorf("vault is sealed")
	}

	return nil
}

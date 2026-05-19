package security

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"golang.org/x/crypto/pbkdf2"
	"ssl-manager/internal/config"
)

type HSMProvider interface {
	Encrypt(plaintext []byte, keyID string) ([]byte, error)
	Decrypt(ciphertext []byte, keyID string) ([]byte, error)
}

type SoftwareHSM struct {
	masterKey []byte
}

func NewSoftwareHSM(keyFilePath string) (*SoftwareHSM, error) {
	keyData, err := os.ReadFile(keyFilePath)
	if err != nil {
		return nil, fmt.Errorf("read master key file failed: %w", err)
	}

	masterKey := pbkdf2.Key(keyData, []byte("ssl-manager-salt"), 100000, 32, sha256.New)

	return &SoftwareHSM{
		masterKey: masterKey,
	}, nil
}

func GenerateMasterKey() ([]byte, error) {
	key := make([]byte, 32)
	_, err := rand.Read(key)
	if err != nil {
		return nil, fmt.Errorf("generate master key failed: %w", err)
	}
	return key, nil
}

func (h *SoftwareHSM) Encrypt(plaintext []byte, keyID string) ([]byte, error) {
	block, err := aes.NewCipher(h.masterKey)
	if err != nil {
		return nil, fmt.Errorf("create aes cipher failed: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("create gcm failed: %w", err)
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("generate nonce failed: %w", err)
	}

	aad := []byte(keyID)
	ciphertext := gcm.Seal(nonce, nonce, plaintext, aad)

	return ciphertext, nil
}

func (h *SoftwareHSM) Decrypt(ciphertext []byte, keyID string) ([]byte, error) {
	block, err := aes.NewCipher(h.masterKey)
	if err != nil {
		return nil, fmt.Errorf("create aes cipher failed: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("create gcm failed: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("ciphertext too short")
	}

	nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
	aad := []byte(keyID)

	plaintext, err := gcm.Open(nil, nonce, ciphertext, aad)
	if err != nil {
		return nil, fmt.Errorf("decrypt failed: %w", err)
	}

	return plaintext, nil
}

type KeyManager struct {
	hsm       HSMProvider
	encryptDir string
}

func NewKeyManager(cfg config.HSMConfig) (*KeyManager, error) {
	if !cfg.Enabled {
		return nil, nil
	}

	var hsm HSMProvider
	var err error

	switch cfg.Provider {
	case "software":
		hsm, err = NewSoftwareHSM(cfg.KeyFilePath)
		if err != nil {
			return nil, fmt.Errorf("create software hsm failed: %w", err)
		}
	default:
		return nil, fmt.Errorf("unsupported hsm provider: %s", cfg.Provider)
	}

	if err := os.MkdirAll(cfg.EncryptDir, 0700); err != nil {
		return nil, fmt.Errorf("create encrypt directory failed: %w", err)
	}

	return &KeyManager{
		hsm:        hsm,
		encryptDir: cfg.EncryptDir,
	}, nil
}

func (km *KeyManager) StorePrivateKey(keyName string, privateKey []byte) error {
	encryptedKey, err := km.hsm.Encrypt(privateKey, keyName)
	if err != nil {
		return fmt.Errorf("encrypt private key failed: %w", err)
	}

	encodedKey := base64.StdEncoding.EncodeToString(encryptedKey)
	keyPath := filepath.Join(km.encryptDir, keyName+".enc")

	if err := os.WriteFile(keyPath, []byte(encodedKey), 0600); err != nil {
		return fmt.Errorf("write encrypted key failed: %w", err)
	}

	return nil
}

func (km *KeyManager) LoadPrivateKey(keyName string) ([]byte, error) {
	keyPath := filepath.Join(km.encryptDir, keyName+".enc")

	encodedKey, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, fmt.Errorf("read encrypted key failed: %w", err)
	}

	encryptedKey, err := base64.StdEncoding.DecodeString(string(encodedKey))
	if err != nil {
		return nil, fmt.Errorf("decode key failed: %w", err)
	}

	privateKey, err := km.hsm.Decrypt(encryptedKey, keyName)
	if err != nil {
		return nil, fmt.Errorf("decrypt private key failed: %w", err)
	}

	return privateKey, nil
}

func (km *KeyManager) DeletePrivateKey(keyName string) error {
	keyPath := filepath.Join(km.encryptDir, keyName+".enc")
	if err := os.Remove(keyPath); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("delete encrypted key failed: %w", err)
	}
	return nil
}

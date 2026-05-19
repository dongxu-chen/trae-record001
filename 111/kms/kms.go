package kms

import (
	"crypto/aes"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/minio/minio-go/v7/pkg/encrypt"
)

const (
	KeyTypeAES256 = "AES256"
	DefaultKeyID  = "default-key"
)

type KeyMetadata struct {
	KeyID        string    `json:"key_id"`
	KeyType      string    `json:"key_type"`
	CreatedAt    time.Time `json:"created_at"`
	Enabled      bool      `json:"enabled"`
	Description  string    `json:"description"`
}

type KeyManager struct {
	keys map[string][]byte
	meta map[string]*KeyMetadata
	mu   sync.RWMutex
}

var defaultKMS *KeyManager

func InitKMS() error {
	defaultKMS = &KeyManager{
		keys: make(map[string][]byte),
		meta: make(map[string]*KeyMetadata),
	}

	key, err := generateAES256Key()
	if err != nil {
		return fmt.Errorf("failed to generate default key: %w", err)
	}

	defaultKMS.keys[DefaultKeyID] = key
	defaultKMS.meta[DefaultKeyID] = &KeyMetadata{
		KeyID:       DefaultKeyID,
		KeyType:     KeyTypeAES256,
		CreatedAt:   time.Now(),
		Enabled:     true,
		Description: "Default AES-256 encryption key",
	}

	return nil
}

func generateAES256Key() ([]byte, error) {
	key := make([]byte, 32)
	_, err := rand.Read(key)
	if err != nil {
		return nil, err
	}
	return key, nil
}

func CreateKey(keyID string, description string) (*KeyMetadata, error) {
	defaultKMS.mu.Lock()
	defer defaultKMS.mu.Unlock()

	if _, exists := defaultKMS.keys[keyID]; exists {
		return nil, errors.New("key already exists")
	}

	key, err := generateAES256Key()
	if err != nil {
		return nil, err
	}

	defaultKMS.keys[keyID] = key
	meta := &KeyMetadata{
		KeyID:       keyID,
		KeyType:     KeyTypeAES256,
		CreatedAt:   time.Now(),
		Enabled:     true,
		Description: description,
	}
	defaultKMS.meta[keyID] = meta

	return meta, nil
}

func GetKey(keyID string) ([]byte, error) {
	defaultKMS.mu.RLock()
	defer defaultKMS.mu.RUnlock()

	key, exists := defaultKMS.keys[keyID]
	if !exists {
		return nil, errors.New("key not found")
	}

	if !defaultKMS.meta[keyID].Enabled {
		return nil, errors.New("key is disabled")
	}

	return key, nil
}

func GetKeyMetadata(keyID string) (*KeyMetadata, error) {
	defaultKMS.mu.RLock()
	defer defaultKMS.mu.RUnlock()

	meta, exists := defaultKMS.meta[keyID]
	if !exists {
		return nil, errors.New("key not found")
	}

	return meta, nil
}

func ListKeys() []*KeyMetadata {
	defaultKMS.mu.RLock()
	defer defaultKMS.mu.RUnlock()

	keys := make([]*KeyMetadata, 0, len(defaultKMS.meta))
	for _, meta := range defaultKMS.meta {
		keys = append(keys, meta)
	}
	return keys
}

func EnableKey(keyID string) error {
	defaultKMS.mu.Lock()
	defer defaultKMS.mu.Unlock()

	meta, exists := defaultKMS.meta[keyID]
	if !exists {
		return errors.New("key not found")
	}
	meta.Enabled = true
	return nil
}

func DisableKey(keyID string) error {
	defaultKMS.mu.Lock()
	defer defaultKMS.mu.Unlock()

	meta, exists := defaultKMS.meta[keyID]
	if !exists {
		return errors.New("key not found")
	}
	meta.Enabled = false
	return nil
}

func GetMinioEncryption(keyID string) (encrypt.ServerSide, error) {
	key, err := GetKey(keyID)
	if err != nil {
		return nil, err
	}

	return encrypt.NewSSEC(key), nil
}

func RotateKey(keyID string) (*KeyMetadata, error) {
	defaultKMS.mu.Lock()
	defer defaultKMS.mu.Unlock()

	if _, exists := defaultKMS.keys[keyID]; !exists {
		return nil, errors.New("key not found")
	}

	newKey, err := generateAES256Key()
	if err != nil {
		return nil, err
	}

	defaultKMS.keys[keyID] = newKey
	defaultKMS.meta[keyID].CreatedAt = time.Now()

	return defaultKMS.meta[keyID], nil
}

func ExportKey(keyID string) (string, error) {
	key, err := GetKey(keyID)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(key), nil
}

func ImportKey(keyID string, encodedKey string, description string) (*KeyMetadata, error) {
	key, err := base64.StdEncoding.DecodeString(encodedKey)
	if err != nil {
		return nil, errors.New("invalid base64 encoded key")
	}

	if len(key) != 32 {
		return nil, errors.New("invalid key length, must be 32 bytes for AES-256")
	}

	defaultKMS.mu.Lock()
	defer defaultKMS.mu.Unlock()

	defaultKMS.keys[keyID] = key
	defaultKMS.meta[keyID] = &KeyMetadata{
		KeyID:       keyID,
		KeyType:     KeyTypeAES256,
		CreatedAt:   time.Now(),
		Enabled:     true,
		Description: description,
	}

	return defaultKMS.meta[keyID], nil
}

func GenerateDataKey(keyID string) (plaintext []byte, ciphertext []byte, err error) {
	kek, err := GetKey(keyID)
	if err != nil {
		return nil, nil, err
	}

	plaintext = make([]byte, 32)
	_, err = rand.Read(plaintext)
	if err != nil {
		return nil, nil, err
	}

	block, err := aes.NewCipher(kek)
	if err != nil {
		return nil, nil, err
	}

	ciphertext = make([]byte, len(plaintext))
	for i := range plaintext {
		ciphertext[i] = plaintext[i] ^ kek[i%len(kek)]
	}

	return plaintext, ciphertext, nil
}

func DecryptDataKey(keyID string, ciphertext []byte) ([]byte, error) {
	kek, err := GetKey(keyID)
	if err != nil {
		return nil, err
	}

	plaintext := make([]byte, len(ciphertext))
	for i := range ciphertext {
		plaintext[i] = ciphertext[i] ^ kek[i%len(kek)]
	}

	return plaintext, nil
}

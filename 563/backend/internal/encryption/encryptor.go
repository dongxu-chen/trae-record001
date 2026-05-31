package encryption

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"os"

	"golang.org/x/crypto/pbkdf2"
)

type Encryptor struct {
	key     []byte
	enabled bool
}

const (
	saltSize   = 16
	keySize    = 32
	iterations = 100000
)

func NewEncryptor(encryptionKey string, enabled bool) (*Encryptor, error) {
	if !enabled {
		return &Encryptor{enabled: false}, nil
	}

	if encryptionKey == "" {
		return nil, errors.New("encryption key is required when encryption is enabled")
	}

	salt := make([]byte, saltSize)
	if _, err := rand.Read(salt); err != nil {
		return nil, fmt.Errorf("failed to generate salt: %w", err)
	}

	key := pbkdf2.Key([]byte(encryptionKey), salt, iterations, keySize, sha256.New)

	return &Encryptor{
		key:     key,
		enabled: true,
	}, nil
}

func NewEncryptorFromKeyFile(keyPath string, enabled bool) (*Encryptor, error) {
	if !enabled {
		return &Encryptor{enabled: false}, nil
	}

	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read key file: %w", err)
	}

	return &Encryptor{
		key:     keyBytes,
		enabled: true,
	}, nil
}

func (e *Encryptor) Encrypt(data []byte) ([]byte, error) {
	if !e.enabled {
		return data, nil
	}

	block, err := aes.NewCipher(e.key)
	if err != nil {
		return nil, fmt.Errorf("failed to create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("failed to create GCM: %w", err)
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("failed to generate nonce: %w", err)
	}

	ciphertext := gcm.Seal(nonce, nonce, data, nil)
	return ciphertext, nil
}

func (e *Encryptor) Decrypt(data []byte) ([]byte, error) {
	if !e.enabled {
		return data, nil
	}

	block, err := aes.NewCipher(e.key)
	if err != nil {
		return nil, fmt.Errorf("failed to create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("failed to create GCM: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(data) < nonceSize {
		return nil, errors.New("ciphertext too short")
	}

	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to decrypt: %w", err)
	}

	return plaintext, nil
}

func (e *Encryptor) EncryptToBase64(data []byte) (string, error) {
	encrypted, err := e.Encrypt(data)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(encrypted), nil
}

func (e *Encryptor) DecryptFromBase64(encoded string) ([]byte, error) {
	data, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return nil, fmt.Errorf("failed to decode base64: %w", err)
	}
	return e.Decrypt(data)
}

func (e *Encryptor) EncryptFile(inputPath, outputPath string) error {
	if !e.enabled {
		input, err := os.ReadFile(inputPath)
		if err != nil {
			return fmt.Errorf("failed to read input file: %w", err)
		}
		return os.WriteFile(outputPath, input, 0644)
	}

	input, err := os.ReadFile(inputPath)
	if err != nil {
		return fmt.Errorf("failed to read input file: %w", err)
	}

	encrypted, err := e.Encrypt(input)
	if err != nil {
		return err
	}

	return os.WriteFile(outputPath, encrypted, 0644)
}

func (e *Encryptor) DecryptFile(inputPath, outputPath string) error {
	if !e.enabled {
		input, err := os.ReadFile(inputPath)
		if err != nil {
			return fmt.Errorf("failed to read input file: %w", err)
		}
		return os.WriteFile(outputPath, input, 0644)
	}

	input, err := os.ReadFile(inputPath)
	if err != nil {
		return fmt.Errorf("failed to read input file: %w", err)
	}

	decrypted, err := e.Decrypt(input)
	if err != nil {
		return err
	}

	return os.WriteFile(outputPath, decrypted, 0644)
}

func (e *Encryptor) IsEnabled() bool {
	return e.enabled
}

func GenerateEncryptionKey() (string, error) {
	key := make([]byte, keySize)
	if _, err := rand.Read(key); err != nil {
		return "", fmt.Errorf("failed to generate key: %w", err)
	}
	return base64.StdEncoding.EncodeToString(key), nil
}

func SaveEncryptionKeyToFile(key, filePath string) error {
	keyBytes, err := base64.StdEncoding.DecodeString(key)
	if err != nil {
		return fmt.Errorf("failed to decode key: %w", err)
	}
	return os.WriteFile(filePath, keyBytes, 0600)
}

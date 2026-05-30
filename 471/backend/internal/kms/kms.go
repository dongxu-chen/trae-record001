package kms

import (
	"context"
	"encoding/base64"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/kms"
	"github.com/aws/aws-sdk-go-v2/service/kms/types"
	"github.com/sirupsen/logrus"
)

type KMSClient struct {
	client *kms.Client
	log    *logrus.Logger
	keyID  string
}

type Config struct {
	Region     string
	KeyID      string
	AccessKey  string
	SecretKey  string
}

func NewKMSClient(cfg Config, log *logrus.Logger) (*KMSClient, error) {
	var awsCfg aws.Config
	var err error

	if cfg.AccessKey != "" && cfg.SecretKey != "" {
		awsCfg, err = config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(cfg.Region),
		)
	} else {
		awsCfg, err = config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(cfg.Region),
		)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &KMSClient{
		client: kms.NewFromConfig(awsCfg),
		log:    log,
		keyID:  cfg.KeyID,
	}, nil
}

func (kc *KMSClient) Encrypt(ctx context.Context, plaintext []byte) (string, error) {
	input := &kms.EncryptInput{
		KeyId:     aws.String(kc.keyID),
		Plaintext: plaintext,
		EncryptionContext: map[string]string{
			"service": "keymgmt",
		},
	}

	result, err := kc.client.Encrypt(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to encrypt data with KMS: %v", err)
		return "", fmt.Errorf("kms encryption failed: %w", err)
	}

	ciphertext := base64.StdEncoding.EncodeToString(result.CiphertextBlob)
	return ciphertext, nil
}

func (kc *KMSClient) Decrypt(ctx context.Context, ciphertext string) ([]byte, error) {
	ciphertextBlob, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return nil, fmt.Errorf("invalid base64 ciphertext: %w", err)
	}

	input := &kms.DecryptInput{
		CiphertextBlob: ciphertextBlob,
		EncryptionContext: map[string]string{
			"service": "keymgmt",
		},
	}

	result, err := kc.client.Decrypt(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to decrypt data with KMS: %v", err)
		return nil, fmt.Errorf("kms decryption failed: %w", err)
	}

	return result.Plaintext, nil
}

func (kc *KMSClient) GenerateDataKey(ctx context.Context) (plaintext []byte, ciphertext string, err error) {
	input := &kms.GenerateDataKeyInput{
		KeyId:   aws.String(kc.keyID),
		KeySpec: types.DataKeySpecAes256,
	}

	result, err := kc.client.GenerateDataKey(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to generate data key: %v", err)
		return nil, "", fmt.Errorf("data key generation failed: %w", err)
	}

	ciphertext = base64.StdEncoding.EncodeToString(result.CiphertextBlob)
	return result.Plaintext, ciphertext, nil
}

func (kc *KMSClient) ReEncrypt(ctx context.Context, ciphertext string, destinationKeyID string) (string, error) {
	ciphertextBlob, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", fmt.Errorf("invalid base64 ciphertext: %w", err)
	}

	input := &kms.ReEncryptInput{
		CiphertextBlob:   ciphertextBlob,
		DestinationKeyId: aws.String(destinationKeyID),
	}

	result, err := kc.client.ReEncrypt(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to re-encrypt data: %v", err)
		return "", fmt.Errorf("re-encryption failed: %w", err)
	}

	newCiphertext := base64.StdEncoding.EncodeToString(result.CiphertextBlob)
	return newCiphertext, nil
}

func (kc *KMSClient) RotateKey(ctx context.Context) error {
	input := &kms.EnableKeyRotationInput{
		KeyId: aws.String(kc.keyID),
	}

	_, err := kc.client.EnableKeyRotation(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to enable key rotation: %v", err)
		return fmt.Errorf("failed to enable key rotation: %w", err)
	}

	kc.log.Infof("Key rotation enabled for KMS key: %s", kc.keyID)
	return nil
}

func (kc *KMSClient) DescribeKey(ctx context.Context) (*kms.DescribeKeyOutput, error) {
	input := &kms.DescribeKeyInput{
		KeyId: aws.String(kc.keyID),
	}

	result, err := kc.client.DescribeKey(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to describe key: %v", err)
		return nil, fmt.Errorf("failed to describe key: %w", err)
	}

	return result, nil
}

func (kc *KMSClient) Sign(ctx context.Context, message []byte) (string, error) {
	input := &kms.SignInput{
		KeyId:            aws.String(kc.keyID),
		Message:          message,
		SigningAlgorithm: types.SigningAlgorithmSpecRsassaPkcs1V15Sha256,
	}

	result, err := kc.client.Sign(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to sign message: %v", err)
		return "", fmt.Errorf("signing failed: %w", err)
	}

	signature := base64.StdEncoding.EncodeToString(result.Signature)
	return signature, nil
}

func (kc *KMSClient) Verify(ctx context.Context, message []byte, signature string) (bool, error) {
	signatureBlob, err := base64.StdEncoding.DecodeString(signature)
	if err != nil {
		return false, fmt.Errorf("invalid base64 signature: %w", err)
	}

	input := &kms.VerifyInput{
		KeyId:            aws.String(kc.keyID),
		Message:          message,
		Signature:        signatureBlob,
		SigningAlgorithm: types.SigningAlgorithmSpecRsassaPkcs1V15Sha256,
	}

	result, err := kc.client.Verify(ctx, input)
	if err != nil {
		kc.log.Errorf("Failed to verify signature: %v", err)
		return false, fmt.Errorf("verification failed: %w", err)
	}

	return *result.SignatureValid, nil
}

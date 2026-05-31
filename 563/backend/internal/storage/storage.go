package storage

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"etcd-backup-manager/pkg/models"
)

type Storage interface {
	Save(ctx context.Context, key string, data []byte) error
	SaveFile(ctx context.Context, key string, filePath string) error
	Get(ctx context.Context, key string) ([]byte, error)
	GetFile(ctx context.Context, key string, outputPath string) error
	Delete(ctx context.Context, key string) error
	List(ctx context.Context, prefix string) ([]string, error)
	Exists(ctx context.Context, key string) (bool, error)
	GetSize(ctx context.Context, key string) (int64, error)
	GetChecksum(ctx context.Context, key string) (string, error)
}

type LocalStorage struct {
	basePath string
}

func NewLocalStorage(basePath string) (*LocalStorage, error) {
	if err := os.MkdirAll(basePath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create base directory: %w", err)
	}
	return &LocalStorage{basePath: basePath}, nil
}

func (s *LocalStorage) getFullPath(key string) string {
	return filepath.Join(s.basePath, key)
}

func (s *LocalStorage) Save(ctx context.Context, key string, data []byte) error {
	fullPath := s.getFullPath(key)
	dir := filepath.Dir(fullPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}
	return os.WriteFile(fullPath, data, 0644)
}

func (s *LocalStorage) SaveFile(ctx context.Context, key string, filePath string) error {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("failed to read source file: %w", err)
	}
	return s.Save(ctx, key, data)
}

func (s *LocalStorage) Get(ctx context.Context, key string) ([]byte, error) {
	fullPath := s.getFullPath(key)
	return os.ReadFile(fullPath)
}

func (s *LocalStorage) GetFile(ctx context.Context, key string, outputPath string) error {
	data, err := s.Get(ctx, key)
	if err != nil {
		return err
	}
	dir := filepath.Dir(outputPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create output directory: %w", err)
	}
	return os.WriteFile(outputPath, data, 0644)
}

func (s *LocalStorage) Delete(ctx context.Context, key string) error {
	fullPath := s.getFullPath(key)
	return os.Remove(fullPath)
}

func (s *LocalStorage) List(ctx context.Context, prefix string) ([]string, error) {
	fullPath := s.getFullPath(prefix)
	var files []string

	err := filepath.Walk(fullPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			relPath, err := filepath.Rel(s.basePath, path)
			if err == nil {
				files = append(files, filepath.ToSlash(relPath))
			}
		}
		return nil
	})

	if os.IsNotExist(err) {
		return []string{}, nil
	}
	return files, err
}

func (s *LocalStorage) Exists(ctx context.Context, key string) (bool, error) {
	fullPath := s.getFullPath(key)
	_, err := os.Stat(fullPath)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, err
}

func (s *LocalStorage) GetSize(ctx context.Context, key string) (int64, error) {
	fullPath := s.getFullPath(key)
	info, err := os.Stat(fullPath)
	if err != nil {
		return 0, err
	}
	return info.Size(), nil
}

func (s *LocalStorage) GetChecksum(ctx context.Context, key string) (string, error) {
	fullPath := s.getFullPath(key)
	file, err := os.Open(fullPath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := md5.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

type S3Storage struct {
	client *minio.Client
	bucket string
}

func NewS3Storage(endpoint, bucket, accessKey, secretKey, region string, useSSL bool) (*S3Storage, error) {
	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: useSSL,
		Region: region,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create S3 client: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	exists, err := client.BucketExists(ctx, bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to check bucket existence: %w", err)
	}
	if !exists {
		if err := client.MakeBucket(ctx, bucket, minio.MakeBucketOptions{Region: region}); err != nil {
			return nil, fmt.Errorf("failed to create bucket: %w", err)
		}
	}

	return &S3Storage{client: client, bucket: bucket}, nil
}

func (s *S3Storage) Save(ctx context.Context, key string, data []byte) error {
	reader := strings.NewReader(string(data))
	_, err := s.client.PutObject(ctx, s.bucket, key, reader, int64(len(data)), minio.PutObjectOptions{
		ContentType: "application/octet-stream",
	})
	return err
}

func (s *S3Storage) SaveFile(ctx context.Context, key string, filePath string) error {
	info, err := os.Stat(filePath)
	if err != nil {
		return err
	}
	_, err = s.client.FPutObject(ctx, s.bucket, key, filePath, minio.PutObjectOptions{
		ContentType: "application/octet-stream",
	})
	_ = info
	return err
}

func (s *S3Storage) Get(ctx context.Context, key string) ([]byte, error) {
	obj, err := s.client.GetObject(ctx, s.bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, err
	}
	defer obj.Close()
	return io.ReadAll(obj)
}

func (s *S3Storage) GetFile(ctx context.Context, key string, outputPath string) error {
	return s.client.FGetObject(ctx, s.bucket, key, outputPath, minio.GetObjectOptions{})
}

func (s *S3Storage) Delete(ctx context.Context, key string) error {
	return s.client.RemoveObject(ctx, s.bucket, key, minio.RemoveObjectOptions{})
}

func (s *S3Storage) List(ctx context.Context, prefix string) ([]string, error) {
	var keys []string
	for obj := range s.client.ListObjects(ctx, s.bucket, minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	}) {
		if obj.Err != nil {
			return nil, obj.Err
		}
		keys = append(keys, obj.Key)
	}
	return keys, nil
}

func (s *S3Storage) Exists(ctx context.Context, key string) (bool, error) {
	_, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err == nil {
		return true, nil
	}
	if minio.ToErrorResponse(err).Code == "NoSuchKey" {
		return false, nil
	}
	return false, err
}

func (s *S3Storage) GetSize(ctx context.Context, key string) (int64, error) {
	info, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		return 0, err
	}
	return info.Size, nil
}

func (s *S3Storage) GetChecksum(ctx context.Context, key string) (string, error) {
	info, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		return "", err
	}
	etag := strings.Trim(info.ETag, "\"")
	return etag, nil
}

func NewStorage(config models.StorageConfig) (Storage, error) {
	switch config.Type {
	case "local":
		return NewLocalStorage(config.LocalPath)
	case "s3":
		return NewS3Storage(
			config.S3Endpoint,
			config.S3Bucket,
			config.AccessKey,
			config.SecretKey,
			config.S3Region,
			config.UseSSL,
		)
	default:
		return nil, fmt.Errorf("unsupported storage type: %s", config.Type)
	}
}

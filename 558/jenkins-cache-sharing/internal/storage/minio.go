package storage

import (
	"context"
	"fmt"
	"io"
	"path"
	"strings"
	"time"

	"github.com/jenkins-cache-sharing/internal/config"
	"github.com/jenkins-cache-sharing/internal/model"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"go.uber.org/zap"
)

type ObjectStorage struct {
	client *minio.Client
	bucket string
	logger *zap.Logger
}

func NewObjectStorage(cfg config.StorageConfig, logger *zap.Logger) (*ObjectStorage, error) {
	client, err := minio.New(cfg.Endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
		Secure: cfg.UseSSL,
		Region: cfg.Region,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create minio client: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	exists, err := client.BucketExists(ctx, cfg.Bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to check bucket: %w", err)
	}
	if !exists {
		if err := client.MakeBucket(ctx, cfg.Bucket, minio.MakeBucketOptions{Region: cfg.Region}); err != nil {
			return nil, fmt.Errorf("failed to create bucket: %w", err)
		}
		logger.Info("created bucket", zap.String("bucket", cfg.Bucket))
	}

	return &ObjectStorage{
		client: client,
		bucket: cfg.Bucket,
		logger: logger,
	}, nil
}

func (s *ObjectStorage) Upload(ctx context.Context, cacheType model.CacheType, jobName string, buildNumber int, reader io.Reader, size int64, version string) (string, error) {
	objectKey := fmt.Sprintf("%s/%s/%d/%s.tar.gz", cacheType, jobName, buildNumber, version)

	opts := minio.PutObjectOptions{
		ContentType: "application/gzip",
		UserMetadata: map[string]string{
			"X-Cache-Type":    string(cacheType),
			"X-Job-Name":      jobName,
			"X-Build-Number":  fmt.Sprintf("%d", buildNumber),
			"X-Cache-Version": version,
		},
	}

	info, err := s.client.PutObject(ctx, s.bucket, objectKey, reader, size, opts)
	if err != nil {
		return "", fmt.Errorf("failed to upload object: %w", err)
	}

	s.logger.Info("uploaded cache object",
		zap.String("key", objectKey),
		zap.String("etag", info.ETag),
		zap.Int64("size", info.Size),
	)

	return objectKey, nil
}

func (s *ObjectStorage) Download(ctx context.Context, objectKey string) (io.ReadCloser, int64, error) {
	info, err := s.client.StatObject(ctx, s.bucket, objectKey, minio.StatObjectOptions{})
	if err != nil {
		return nil, 0, fmt.Errorf("failed to stat object: %w", err)
	}

	reader, err := s.client.GetObject(ctx, s.bucket, objectKey, minio.GetObjectOptions{})
	if err != nil {
		return nil, 0, fmt.Errorf("failed to get object: %w", err)
	}

	return reader, info.Size, nil
}

func (s *ObjectStorage) Delete(ctx context.Context, objectKey string) error {
	err := s.client.RemoveObject(ctx, s.bucket, objectKey, minio.RemoveObjectOptions{})
	if err != nil {
		return fmt.Errorf("failed to delete object: %w", err)
	}
	s.logger.Info("deleted cache object", zap.String("key", objectKey))
	return nil
}

func (s *ObjectStorage) DeleteBatch(ctx context.Context, objectKeys []string) error {
	objectsCh := make(chan minio.ObjectInfo, len(objectKeys))
	go func() {
		defer close(objectsCh)
		for _, key := range objectKeys {
			objectsCh <- minio.ObjectInfo{Key: key}
		}
	}()

	for err := range s.client.RemoveObjects(ctx, s.bucket, objectsCh, minio.RemoveObjectsOptions{}) {
		if err.Err != nil {
			s.logger.Error("failed to delete object", zap.Error(err.Err))
			return fmt.Errorf("failed to delete object: %w", err.Err)
		}
	}

	s.logger.Info("batch deleted objects", zap.Int("count", len(objectKeys)))
	return nil
}

type StorageObjectInfo struct {
	Key          string
	Size         int64
	LastModified time.Time
	ETag         string
	Metadata     map[string]string
}

func (s *ObjectStorage) ListByPrefix(ctx context.Context, prefix string) ([]StorageObjectInfo, error) {
	var objects []StorageObjectInfo

	for object := range s.client.ListObjects(ctx, s.bucket, minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	}) {
		if object.Err != nil {
			return nil, fmt.Errorf("failed to list objects: %w", object.Err)
		}
		objects = append(objects, StorageObjectInfo{
			Key:          object.Key,
			Size:         object.Size,
			LastModified: object.LastModified,
			ETag:         object.ETag,
		})
	}

	return objects, nil
}

func (s *ObjectStorage) GetSizeByType(ctx context.Context, cacheType model.CacheType) (int64, int, error) {
	prefix := string(cacheType) + "/"
	var totalSize int64
	var count int

	for object := range s.client.ListObjects(ctx, s.bucket, minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	}) {
		if object.Err != nil {
			return 0, 0, fmt.Errorf("failed to list objects: %w", object.Err)
		}
		totalSize += object.Size
		count++
	}

	return totalSize, count, nil
}

func (s *ObjectStorage) GetPresignedURL(ctx context.Context, objectKey string, expiry time.Duration) (string, error) {
	reqParams := make(map[string]string)
	url, err := s.client.PresignedGetObject(ctx, s.bucket, objectKey, expiry, reqParams)
	if err != nil {
		return "", fmt.Errorf("failed to generate presigned URL: %w", err)
	}
	return url.String(), nil
}

func BuildObjectKey(cacheType model.CacheType, jobName string, buildNumber int, version string) string {
	return path.Join(string(cacheType), jobName, fmt.Sprintf("%d", buildNumber), version+".tar.gz")
}

func ParseObjectKey(key string) (model.CacheType, string, int, string, error) {
	parts := strings.Split(key, "/")
	if len(parts) < 4 {
		return "", "", 0, "", fmt.Errorf("invalid object key format: %s", key)
	}
	var buildNumber int
	fmt.Sscanf(parts[2], "%d", &buildNumber)
	version := strings.TrimSuffix(parts[3], ".tar.gz")
	return model.CacheType(parts[0]), parts[1], buildNumber, version, nil
}

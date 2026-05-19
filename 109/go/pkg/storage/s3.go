package storage

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/feature/s3/manager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

type S3Storage struct {
	client *s3.Client
	cfg    *config.S3Config
}

func NewS3Storage(s3Cfg *config.S3Config) (*S3Storage, error) {
	cred := credentials.NewStaticCredentialsProvider(
		s3Cfg.AccessKey,
		s3Cfg.SecretKey,
		"",
	)

	customResolver := aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
		if !strings.HasPrefix(s3Cfg.Endpoint, "http://") && !strings.HasPrefix(s3Cfg.Endpoint, "https://") {
			if s3Cfg.UseSSL {
				s3Cfg.Endpoint = "https://" + s3Cfg.Endpoint
			} else {
				s3Cfg.Endpoint = "http://" + s3Cfg.Endpoint
			}
		}

		return aws.Endpoint{
			URL:           s3Cfg.Endpoint,
			SigningRegion: s3Cfg.Region,
		}, nil
	})

	cfg := aws.Config{
		Credentials:      cred,
		Region:           s3Cfg.Region,
		EndpointResolver: customResolver,
	}

	client := s3.NewFromConfig(cfg, func(o *s3.Options) {
		o.UsePathStyle = s3Cfg.PathStyle
	})

	storage := &S3Storage{
		client: client,
		cfg:    s3Cfg,
	}

	if err := storage.ensureBucket(); err != nil {
		return nil, fmt.Errorf("failed to ensure bucket: %w", err)
	}

	logger.Info("S3 storage initialized successfully")
	return storage, nil
}

func (s *S3Storage) ensureBucket() error {
	_, err := s.client.HeadBucket(context.TODO(), &s3.HeadBucketInput{
		Bucket: aws.String(s.cfg.Bucket),
	})

	if err != nil {
		if _, ok := err.(*types.NotFound); ok {
			logger.Infof("Bucket %s not found, creating...", s.cfg.Bucket)

			_, createErr := s.client.CreateBucket(context.TODO(), &s3.CreateBucketInput{
				Bucket: aws.String(s.cfg.Bucket),
			})

			if createErr != nil {
				return fmt.Errorf("failed to create bucket: %w", createErr)
			}
		} else {
			return fmt.Errorf("failed to check bucket: %w", err)
		}
	}

	return nil
}

func (s *S3Storage) Upload(ctx context.Context, filePath string) error {
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	fileInfo, err := file.Stat()
	if err != nil {
		return fmt.Errorf("failed to get file info: %w", err)
	}

	key := filepath.Join(s.cfg.Prefix, filepath.Base(filePath))
	uploader := manager.NewUploader(s.client, func(u *manager.Uploader) {
		u.PartSize = 5 * 1024 * 1024
		u.Concurrency = 5
	})

	_, err = uploader.Upload(ctx, &s3.PutObjectInput{
		Bucket:        aws.String(s.cfg.Bucket),
		Key:           aws.String(key),
		Body:          file,
		ContentLength: aws.Int64(fileInfo.Size()),
	})

	if err != nil {
		return fmt.Errorf("failed to upload file: %w", err)
	}

	logger.Infof("Successfully uploaded %s to s3://%s/%s", filePath, s.cfg.Bucket, key)
	return nil
}

func (s *S3Storage) Download(ctx context.Context, key string, destPath string) error {
	downloader := manager.NewDownloader(s.client)

	file, err := os.Create(destPath)
	if err != nil {
		return fmt.Errorf("failed to create destination file: %w", err)
	}
	defer file.Close()

	_, err = downloader.Download(ctx, file, &s3.GetObjectInput{
		Bucket: aws.String(s.cfg.Bucket),
		Key:    aws.String(key),
	})

	if err != nil {
		return fmt.Errorf("failed to download file: %w", err)
	}

	logger.Infof("Successfully downloaded s3://%s/%s to %s", s.cfg.Bucket, key, destPath)
	return nil
}

func (s *S3Storage) Delete(ctx context.Context, key string) error {
	_, err := s.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(s.cfg.Bucket),
		Key:    aws.String(key),
	})

	if err != nil {
		return fmt.Errorf("failed to delete object: %w", err)
	}

	logger.Infof("Successfully deleted s3://%s/%s", s.cfg.Bucket, key)
	return nil
}

func (s *S3Storage) List(ctx context.Context, prefix string) ([]string, error) {
	if prefix == "" {
		prefix = s.cfg.Prefix
	}

	var keys []string
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{
		Bucket: aws.String(s.cfg.Bucket),
		Prefix: aws.String(prefix),
	})

	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list objects: %w", err)
		}

		for _, obj := range page.Contents {
			keys = append(keys, *obj.Key)
		}
	}

	return keys, nil
}

func (s *S3Storage) Exists(ctx context.Context, key string) (bool, error) {
	_, err := s.client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(s.cfg.Bucket),
		Key:    aws.String(key),
	})

	if err != nil {
		if _, ok := err.(*types.NotFound); ok {
			return false, nil
		}
		return false, err
	}

	return true, nil
}

type Storage interface {
	Upload(ctx context.Context, filePath string) error
	Download(ctx context.Context, key string, destPath string) error
	Delete(ctx context.Context, key string) error
	List(ctx context.Context, prefix string) ([]string, error)
	Exists(ctx context.Context, key string) (bool, error)
}

func NewStorage(cfg *config.StorageConfig) (Storage, error) {
	switch cfg.Type {
	case "s3":
		return NewS3Storage(&cfg.S3)
	default:
		return nil, fmt.Errorf("unsupported storage type: %s", cfg.Type)
	}
}

package storage

import (
	"bytes"
	"context"
	"io"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type S3Storage struct {
	client *minio.Client
	bucket string
}

func NewS3Storage(config Config) (Storage, error) {
	opts := &minio.Options{
		Creds:  credentials.NewStaticV4(config.AccessKey, config.SecretKey, ""),
		Secure: config.UseSSL,
	}

	if config.Region != "" {
		opts.Region = config.Region
	}

	client, err := minio.New(config.Endpoint, opts)
	if err != nil {
		return nil, err
	}

	ctx := context.Background()
	exists, err := client.BucketExists(ctx, config.Bucket)
	if err != nil {
		return nil, err
	}

	if !exists {
		if err := client.MakeBucket(ctx, config.Bucket, minio.MakeBucketOptions{
			Region: config.Region,
		}); err != nil {
			return nil, err
		}
	}

	return &S3Storage{
		client: client,
		bucket: config.Bucket,
	}, nil
}

func (s *S3Storage) Upload(ctx context.Context, key string, reader io.Reader, size int64) error {
	_, err := s.client.PutObject(ctx, s.bucket, key, reader, size, minio.PutObjectOptions{})
	return err
}

func (s *S3Storage) Download(ctx context.Context, key string) (io.ReadCloser, error) {
	obj, err := s.client.GetObject(ctx, s.bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return nil, err
	}
	return obj, nil
}

func (s *S3Storage) Exists(ctx context.Context, key string) (bool, error) {
	_, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		errResponse := minio.ToErrorResponse(err)
		if errResponse.Code == "NoSuchKey" {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (s *S3Storage) Delete(ctx context.Context, key string) error {
	return s.client.RemoveObject(ctx, s.bucket, key, minio.RemoveObjectOptions{})
}

func (s *S3Storage) List(ctx context.Context, prefix string) ([]ObjectInfo, error) {
	var objects []ObjectInfo

	opts := minio.ListObjectsOptions{
		Prefix:    prefix,
		Recursive: true,
	}

	for obj := range s.client.ListObjects(ctx, s.bucket, opts) {
		if obj.Err != nil {
			return nil, obj.Err
		}

		objects = append(objects, ObjectInfo{
			Key:          obj.Key,
			Size:         obj.Size,
			LastModified: obj.LastModified,
			ETag:         obj.ETag,
		})
	}

	return objects, nil
}

func (s *S3Storage) GetInfo(ctx context.Context, key string) (*ObjectInfo, error) {
	stat, err := s.client.StatObject(ctx, s.bucket, key, minio.StatObjectOptions{})
	if err != nil {
		return nil, err
	}

	return &ObjectInfo{
		Key:          key,
		Size:         stat.Size,
		LastModified: stat.LastModified,
		ETag:         stat.ETag,
		Metadata:     make(map[string]string),
	}, nil
}

func (s *S3Storage) Close() error {
	return nil
}

func init() {
	Register("s3", NewS3Storage)
}

func UploadBytes(ctx context.Context, s Storage, key string, data []byte) error {
	return s.Upload(ctx, key, bytes.NewReader(data), int64(len(data)))
}

func DownloadBytes(ctx context.Context, s Storage, key string) ([]byte, error) {
	reader, err := s.Download(ctx, key)
	if err != nil {
		return nil, err
	}
	defer reader.Close()

	return io.ReadAll(reader)
}

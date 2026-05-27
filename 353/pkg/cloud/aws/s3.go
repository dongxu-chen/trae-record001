package aws

import (
	"bytes"
	"context"
	"fmt"
	"io"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/cloud-migration-tool/pkg/cloud"
)

type S3Client struct {
	client *s3.Client
	region string
}

func NewS3Client(region string) (*S3Client, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(region))
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &S3Client{
		client: s3.NewFromConfig(cfg),
		region: region,
	}, nil
}

func (s *S3Client) GetProviderName() string {
	return "aws"
}

func (s *S3Client) GetRegion() string {
	return s.region
}

func (s *S3Client) ListObjects(ctx context.Context, bucket string, prefix string) ([]cloud.ObjectInfo, error) {
	var objects []cloud.ObjectInfo
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{
		Bucket: aws.String(bucket),
		Prefix: aws.String(prefix),
	})

	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list objects: %w", err)
		}

		for _, obj := range page.Contents {
			objects = append(objects, cloud.ObjectInfo{
				Key:          *obj.Key,
				Size:         obj.Size,
				LastModified: obj.LastModified.Unix(),
				ETag:         *obj.ETag,
			})
		}
	}

	return objects, nil
}

func (s *S3Client) DownloadObject(ctx context.Context, bucket string, key string) ([]byte, error) {
	resp, err := s.client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to download object: %w", err)
	}
	defer resp.Body.Close()

	return io.ReadAll(resp.Body)
}

func (s *S3Client) UploadObject(ctx context.Context, bucket string, key string, data []byte) error {
	_, err := s.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
		Body:   bytes.NewReader(data),
	})
	if err != nil {
		return fmt.Errorf("failed to upload object: %w", err)
	}
	return nil
}

func (s *S3Client) CopyObject(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string) error {
	copySource := fmt.Sprintf("%s/%s", srcBucket, srcKey)
	_, err := s.client.CopyObject(ctx, &s3.CopyObjectInput{
		Bucket:     aws.String(dstBucket),
		Key:        aws.String(dstKey),
		CopySource: aws.String(copySource),
	})
	if err != nil {
		return fmt.Errorf("failed to copy object: %w", err)
	}
	return nil
}

func (s *S3Client) GetObjectMetadata(ctx context.Context, bucket string, key string) (*cloud.ObjectInfo, error) {
	resp, err := s.client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get object metadata: %w", err)
	}

	return &cloud.ObjectInfo{
		Key:          key,
		Size:         resp.ContentLength,
		LastModified: resp.LastModified.Unix(),
		ETag:         *resp.ETag,
	}, nil
}

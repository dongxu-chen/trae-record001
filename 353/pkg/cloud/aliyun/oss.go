package aliyun

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/aliyun/aliyun-oss-go-sdk/oss"
	"github.com/cloud-migration-tool/pkg/cloud"
)

type OSSClient struct {
	client *oss.Client
	region string
}

func NewOSSClient(region, accessKeyID, accessKeySecret string) (*OSSClient, error) {
	endpoint := fmt.Sprintf("oss-%s.aliyuncs.com", region)
	client, err := oss.New(endpoint, accessKeyID, accessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("failed to create OSS client: %w", err)
	}
	return &OSSClient{
		client: client,
		region: region,
	}, nil
}

func (o *OSSClient) GetProviderName() string {
	return "aliyun"
}

func (o *OSSClient) GetRegion() string {
	return o.region
}

func (o *OSSClient) ListObjects(ctx context.Context, bucket string, prefix string) ([]cloud.ObjectInfo, error) {
	b, err := o.client.Bucket(bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to get bucket: %w", err)
	}

	var objects []cloud.ObjectInfo
	marker := ""

	for {
		opts := []oss.Option{oss.Prefix(prefix), oss.Marker(marker), oss.MaxKeys(1000)}
		result, err := b.ListObjects(opts...)
		if err != nil {
			return nil, fmt.Errorf("failed to list objects: %w", err)
		}

		for _, obj := range result.Objects {
			objects = append(objects, cloud.ObjectInfo{
				Key:          obj.Key,
				Size:         obj.Size,
				LastModified: obj.LastModified.Unix(),
				ETag:         obj.ETag,
			})
		}

		if !result.IsTruncated {
			break
		}
		marker = result.NextMarker
	}

	return objects, nil
}

func (o *OSSClient) DownloadObject(ctx context.Context, bucket string, key string) ([]byte, error) {
	b, err := o.client.Bucket(bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to get bucket: %w", err)
	}

	reader, err := b.GetObject(key)
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %w", err)
	}
	defer reader.Close()

	return io.ReadAll(reader)
}

func (o *OSSClient) UploadObject(ctx context.Context, bucket string, key string, data []byte) error {
	b, err := o.client.Bucket(bucket)
	if err != nil {
		return fmt.Errorf("failed to get bucket: %w", err)
	}

	return b.PutObject(key, bytes.NewReader(data))
}

func (o *OSSClient) CopyObject(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string) error {
	b, err := o.client.Bucket(dstBucket)
	if err != nil {
		return fmt.Errorf("failed to get bucket: %w", err)
	}

	src := fmt.Sprintf("%s/%s", srcBucket, srcKey)
	_, err = b.CopyObject(src, dstKey)
	if err != nil {
		return fmt.Errorf("failed to copy object: %w", err)
	}
	return nil
}

func (o *OSSClient) GetObjectMetadata(ctx context.Context, bucket string, key string) (*cloud.ObjectInfo, error) {
	b, err := o.client.Bucket(bucket)
	if err != nil {
		return nil, fmt.Errorf("failed to get bucket: %w", err)
	}

	meta, err := b.GetObjectDetailedMeta(key)
	if err != nil {
		return nil, fmt.Errorf("failed to get object metadata: %w", err)
	}

	lastModified, _ := time.Parse(http.TimeFormat, meta.Get("Last-Modified"))
	return &cloud.ObjectInfo{
		Key:          key,
		Size:         0,
		LastModified: lastModified.Unix(),
		ETag:         meta.Get("ETag"),
	}, nil
}

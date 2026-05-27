package tencent

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/tencentyun/cos-go-sdk-v5"
	"github.com/cloud-migration-tool/pkg/cloud"
)

type COSClient struct {
	client *cos.Client
	region string
}

func NewCOSClient(region, secretID, secretKey, appID string) (*COSClient, error) {
	u, _ := url.Parse(fmt.Sprintf("https://cos.%s.myqcloud.com", region))
	b := &cos.BaseURL{BucketURL: u}
	client := cos.NewClient(b, &http.Client{
		Transport: &cos.AuthorizationTransport{
			SecretID:  secretID,
			SecretKey: secretKey,
		},
	})
	return &COSClient{
		client: client,
		region: region,
	}, nil
}

func (c *COSClient) GetProviderName() string {
	return "tencent"
}

func (c *COSClient) GetRegion() string {
	return c.region
}

func (c *COSClient) ListObjects(ctx context.Context, bucket string, prefix string) ([]cloud.ObjectInfo, error) {
	var objects []cloud.ObjectInfo
	marker := ""

	for {
		opt := &cos.BucketGetOptions{
			Prefix:  prefix,
			Marker:  marker,
			MaxKeys: 1000,
		}
		result, _, err := c.client.Bucket.Get(ctx, opt)
		if err != nil {
			return nil, fmt.Errorf("failed to list objects: %w", err)
		}

		for _, obj := range result.Contents {
			lastModified, _ := time.Parse(time.RFC3339, obj.LastModified)
			objects = append(objects, cloud.ObjectInfo{
				Key:          obj.Key,
				Size:         obj.Size,
				LastModified: lastModified.Unix(),
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

func (c *COSClient) DownloadObject(ctx context.Context, bucket string, key string) ([]byte, error) {
	resp, err := c.client.Object.Get(ctx, key, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to get object: %w", err)
	}
	defer resp.Body.Close()

	return io.ReadAll(resp.Body)
}

func (c *COSClient) UploadObject(ctx context.Context, bucket string, key string, data []byte) error {
	_, err := c.client.Object.Put(ctx, key, bytes.NewReader(data), nil)
	if err != nil {
		return fmt.Errorf("failed to put object: %w", err)
	}
	return nil
}

func (c *COSClient) CopyObject(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string) error {
	sourceURL := fmt.Sprintf("%s/%s", srcBucket, srcKey)
	_, _, err := c.client.Object.Copy(ctx, dstKey, sourceURL, nil)
	if err != nil {
		return fmt.Errorf("failed to copy object: %w", err)
	}
	return nil
}

func (c *COSClient) GetObjectMetadata(ctx context.Context, bucket string, key string) (*cloud.ObjectInfo, error) {
	resp, err := c.client.Object.Head(ctx, key, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to head object: %w", err)
	}

	lastModified, _ := time.Parse(time.RFC1123, resp.Header.Get("Last-Modified"))
	return &cloud.ObjectInfo{
		Key:          key,
		Size:         resp.ContentLength,
		LastModified: lastModified.Unix(),
		ETag:         resp.Header.Get("ETag"),
	}, nil
}

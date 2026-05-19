package seaweedfs

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"net/url"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/kms"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type Client struct {
	MasterURL    string
	VolumeURL    string
	FilerURL     string
	S3Client     *minio.Client
	HTTPClient   *http.Client
}

type AssignResult struct {
	FID       string `json:"fid"`
	URL       string `json:"url"`
	PublicURL string `json:"publicUrl"`
	Count     int    `json:"count"`
	Error     string `json:"error,omitempty"`
}

type FileInfo struct {
	Name    string    `json:"name"`
	Size    int64     `json:"size"`
	ETag    string    `json:"etag"`
	Modified time.Time `json:"modified"`
}

type ObjectVersion struct {
	Key       string
	VersionID string
	IsLatest  bool
	Size      int64
	LastModified time.Time
}

var (
	SWClient *Client
	once     sync.Once
)

func InitSeaweedFS() error {
	var err error
	once.Do(func() {
		s3Client, initErr := minio.New(config.SeaweedFSS3Endpoint, &minio.Options{
			Creds:  credentials.NewStaticV4(config.SeaweedFSAccessKey, config.SeaweedFSSecretKey, ""),
			Secure: config.SeaweedFSUseSSL,
		})
		if initErr != nil {
			err = initErr
			return
		}

		SWClient = &Client{
			MasterURL:  config.SeaweedFSMasterURL,
			VolumeURL:  config.SeaweedFSVolumeURL,
			FilerURL:   config.SeaweedFSFilerURL,
			S3Client:   s3Client,
			HTTPClient: &http.Client{Timeout: 30 * time.Second},
		}

		ctx := context.Background()
		exists, bucketErr := s3Client.BucketExists(ctx, config.SeaweedFSBucketName)
		if bucketErr != nil {
			err = bucketErr
			return
		}
		if !exists {
			if createErr := s3Client.MakeBucket(ctx, config.SeaweedFSBucketName, minio.MakeBucketOptions{}); createErr != nil {
				err = createErr
				return
			}
			log.Printf("Bucket %s created successfully", config.SeaweedFSBucketName)
		}
	})

	if err == nil {
		log.Println("SeaweedFS client initialized successfully")
	}
	return err
}

func (c *Client) AssignFile(ctx context.Context, replication string, ttl string) (*AssignResult, error) {
	params := url.Values{}
	if replication != "" {
		params.Set("replication", replication)
	}
	if ttl != "" {
		params.Set("ttl", ttl)
	}

	url := fmt.Sprintf("%s/dir/assign?%s", c.MasterURL, params.Encode())
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result AssignResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	if result.Error != "" {
		return nil, fmt.Errorf(result.Error)
	}

	return &result, nil
}

func (c *Client) UploadFile(ctx context.Context, fid string, reader io.Reader, size int64) error {
	url := fmt.Sprintf("%s/%s", c.VolumeURL, fid)
	
	req, err := http.NewRequestWithContext(ctx, "PUT", url, reader)
	if err != nil {
		return err
	}
	req.ContentLength = size

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("upload failed: %s", string(body))
	}

	return nil
}

func (c *Client) DownloadFile(ctx context.Context, fid string) (io.ReadCloser, error) {
	url := fmt.Sprintf("%s/%s", c.VolumeURL, fid)
	
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("download failed: %s", string(body))
	}

	return resp.Body, nil
}

func (c *Client) DeleteFile(ctx context.Context, fid string) error {
	url := fmt.Sprintf("%s/%s", c.VolumeURL, fid)
	
	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent && resp.StatusCode != http.StatusAccepted {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("delete failed: %s", string(body))
	}

	return nil
}

func (c *Client) UploadChunk(ctx context.Context, objectName string, reader io.Reader, size int64) error {
	_, err := c.S3Client.PutObject(ctx, config.SeaweedFSBucketName, objectName, reader, size, minio.PutObjectOptions{})
	return err
}

func (c *Client) UploadChunkWithEncryption(ctx context.Context, objectName string, reader io.Reader, size int64, keyID string) error {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return err
	}

	_, err = c.S3Client.PutObject(ctx, config.SeaweedFSBucketName, objectName, reader, size, minio.PutObjectOptions{
		ServerSideEncryption: sse,
	})
	return err
}

func (c *Client) DownloadFileS3(ctx context.Context, objectName string) (*minio.Object, error) {
	return c.S3Client.GetObject(ctx, config.SeaweedFSBucketName, objectName, minio.GetObjectOptions{})
}

func (c *Client) DownloadFileWithVersion(ctx context.Context, objectName string, versionID string) (*minio.Object, error) {
	opts := minio.GetObjectOptions{}
	if versionID != "" {
		opts.VersionID = versionID
	}
	return c.S3Client.GetObject(ctx, config.SeaweedFSBucketName, objectName, opts)
}

func (c *Client) DownloadFileWithEncryption(ctx context.Context, objectName string, keyID string) (*minio.Object, error) {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return nil, err
	}

	opts := minio.GetObjectOptions{
		ServerSideEncryption: sse,
	}
	return c.S3Client.GetObject(ctx, config.SeaweedFSBucketName, objectName, opts)
}

func (c *Client) DeleteObject(ctx context.Context, objectName string) error {
	return c.S3Client.RemoveObject(ctx, config.SeaweedFSBucketName, objectName, minio.RemoveObjectOptions{})
}

func (c *Client) DeleteObjectVersion(ctx context.Context, objectName string, versionID string) error {
	return c.S3Client.RemoveObject(ctx, config.SeaweedFSBucketName, objectName, minio.RemoveObjectOptions{
		VersionID: versionID,
	})
}

func (c *Client) DeleteObjects(ctx context.Context, objectNames []string) error {
	objectsCh := make(chan minio.ObjectInfo, len(objectNames))
	go func() {
		defer close(objectsCh)
		for _, name := range objectNames {
			objectsCh <- minio.ObjectInfo{Key: name}
		}
	}()

	for err := range c.S3Client.RemoveObjects(ctx, config.SeaweedFSBucketName, objectsCh, minio.RemoveObjectsOptions{}) {
		if err.Err != nil {
			return err.Err
		}
	}
	return nil
}

func (c *Client) ComposeObject(ctx context.Context, destination string, sources []minio.CopySrcOptions) error {
	_, err := c.S3Client.ComposeObject(ctx, minio.ComposeObjectOptions{
		Destination: minio.CopyDestOptions{
			Bucket: config.SeaweedFSBucketName,
			Object: destination,
		},
		Sources: sources,
	})
	return err
}

func (c *Client) ComposeObjectWithEncryption(ctx context.Context, destination string, sources []minio.CopySrcOptions, keyID string) error {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return err
	}

	_, err = c.S3Client.ComposeObject(ctx, minio.ComposeObjectOptions{
		Destination: minio.CopyDestOptions{
			Bucket:               config.SeaweedFSBucketName,
			Object:               destination,
			ServerSideEncryption: sse,
		},
		Sources: sources,
	})
	return err
}

func (c *Client) StatObject(ctx context.Context, objectName string) (minio.ObjectInfo, error) {
	return c.S3Client.StatObject(ctx, config.SeaweedFSBucketName, objectName, minio.StatObjectOptions{})
}

func (c *Client) StatObjectWithVersion(ctx context.Context, objectName string, versionID string) (minio.ObjectInfo, error) {
	opts := minio.StatObjectOptions{}
	if versionID != "" {
		opts.VersionID = versionID
	}
	return c.S3Client.StatObject(ctx, config.SeaweedFSBucketName, objectName, opts)
}

func (c *Client) ListObjectVersions(ctx context.Context, prefix string) ([]minio.ObjectVersion, error) {
	var versions []minio.ObjectVersion

	for object := range c.S3Client.ListObjectVersions(ctx, config.SeaweedFSBucketName, prefix, "", "", 1000) {
		if object.Err != nil {
			return nil, object.Err
		}
		versions = append(versions, object)
	}

	return versions, nil
}

func (c *Client) RestoreObjectVersion(ctx context.Context, objectName string, versionID string) error {
	srcOpts := minio.CopySrcOptions{
		Bucket:    config.SeaweedFSBucketName,
		Object:    objectName,
		VersionID: versionID,
	}

	dstOpts := minio.CopyDestOptions{
		Bucket: config.SeaweedFSBucketName,
		Object: objectName,
	}

	_, err := c.S3Client.CopyObject(ctx, dstOpts, srcOpts)
	return err
}

func (c *Client) GetLifecycle(ctx context.Context) (*minio.LifecycleConfiguration, error) {
	return c.S3Client.GetBucketLifecycle(ctx, config.SeaweedFSBucketName)
}

func (c *Client) SetLifecycle(ctx context.Context, config *minio.LifecycleConfiguration) error {
	return c.S3Client.SetBucketLifecycle(ctx, config.SeaweedFSBucketName, config)
}

func (c *Client) SetObjectExpiration(ctx context.Context, objectName string, days int) error {
	lc, err := c.GetLifecycle(ctx)
	if err != nil {
		lc = &minio.LifecycleConfiguration{}
	}

	ruleID := "expire-" + objectName
	lc.Rules = append(lc.Rules, minio.LifecycleRule{
		ID:     ruleID,
		Status: "Enabled",
		Filter: minio.LifecycleFilter{Prefix: objectName},
		Expiration: minio.LifecycleExpiration{
			Days: minio.LifecycleExpirationDays(days),
		},
	})

	return c.SetLifecycle(ctx, lc)
}

func (c *Client) SetGlobalExpiration(ctx context.Context, days int) error {
	lc := &minio.LifecycleConfiguration{}
	lc.Rules = append(lc.Rules, minio.LifecycleRule{
		ID:     "global-expiration",
		Status: "Enabled",
		Filter: minio.LifecycleFilter{Prefix: ""},
		Expiration: minio.LifecycleExpiration{
			Days: minio.LifecycleExpirationDays(days),
		},
	})

	return c.SetLifecycle(ctx, lc)
}

func (c *Client) SetNoncurrentVersionExpiration(ctx context.Context, days int) error {
	lc, err := c.GetLifecycle(ctx)
	if err != nil {
		lc = &minio.LifecycleConfiguration{}
	}

	lc.Rules = append(lc.Rules, minio.LifecycleRule{
		ID:     "noncurrent-expiration",
		Status: "Enabled",
		Filter: minio.LifecycleFilter{Prefix: ""},
		NoncurrentVersionExpiration: minio.NoncurrentVersionExpiration{
			NoncurrentDays: minio.LifecycleExpirationDays(days),
		},
	})

	return c.SetLifecycle(ctx, lc)
}

func (c *Client) RemoveLifecycleRule(ctx context.Context, ruleID string) error {
	lc, err := c.GetLifecycle(ctx)
	if err != nil {
		return err
	}

	var newRules []minio.LifecycleRule
	for _, rule := range lc.Rules {
		if rule.ID != ruleID {
			newRules = append(newRules, rule)
		}
	}
	lc.Rules = newRules

	return c.SetLifecycle(ctx, lc)
}

func (c *Client) EnableVersioning(ctx context.Context) error {
	config, err := c.S3Client.GetBucketVersioning(ctx, config.SeaweedFSBucketName)
	if err != nil {
		return err
	}
	if config.Status != "Enabled" {
		return c.S3Client.SetBucketVersioning(ctx, config.SeaweedFSBucketName, minio.BucketVersioningConfiguration{
			Status: "Enabled",
		})
	}
	return nil
}

func (c *Client) SuspendVersioning(ctx context.Context) error {
	return c.S3Client.SetBucketVersioning(ctx, config.SeaweedFSBucketName, minio.BucketVersioningConfiguration{
		Status: "Suspended",
	})
}

func (c *Client) GetVersioningStatus(ctx context.Context) (bool, error) {
	config, err := c.S3Client.GetBucketVersioning(ctx, config.SeaweedFSBucketName)
	if err != nil {
		return false, err
	}
	return config.Status == "Enabled", nil
}

func (c *Client) GetS3Client() *minio.Client {
	return c.S3Client
}

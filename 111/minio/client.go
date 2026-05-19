package minio

import (
	"context"
	"io"
	"log"
	"time"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/kms"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/minio/minio-go/v7/pkg/lifecycle"
)

var Client *minio.Client

func InitMinIO() error {
	var err error
	Client, err = minio.New(config.MinIOEndpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(config.MinIOAccessKey, config.MinIOSecretKey, ""),
		Secure: config.MinIOUseSSL,
	})
	if err != nil {
		return err
	}

	ctx := context.Background()
	exists, err := Client.BucketExists(ctx, config.MinIOBucketName)
	if err != nil {
		return err
	}
	if !exists {
		err = Client.MakeBucket(ctx, config.MinIOBucketName, minio.MakeBucketOptions{})
		if err != nil {
			return err
		}
		log.Printf("Bucket %s created successfully", config.MinIOBucketName)
	}

	if err := EnableVersioning(ctx); err != nil {
		log.Printf("Warning: Failed to enable versioning: %v", err)
	} else {
		log.Println("Bucket versioning enabled successfully")
	}

	log.Println("MinIO client initialized successfully")
	return nil
}

func EnableVersioning(ctx context.Context) error {
	config, err := Client.GetBucketVersioning(ctx, config.MinIOBucketName)
	if err != nil {
		return err
	}
	if config.Status != "Enabled" {
		return Client.SetBucketVersioning(ctx, config.MinIOBucketName, minio.BucketVersioningConfiguration{
			Status: "Enabled",
		})
	}
	return nil
}

func SuspendVersioning(ctx context.Context) error {
	return Client.SetBucketVersioning(ctx, config.MinIOBucketName, minio.BucketVersioningConfiguration{
		Status: "Suspended",
	})
}

func GetVersioningStatus(ctx context.Context) (bool, error) {
	config, err := Client.GetBucketVersioning(ctx, config.MinIOBucketName)
	if err != nil {
		return false, err
	}
	return config.Status == "Enabled", nil
}

func UploadChunk(ctx context.Context, objectName string, reader io.Reader, size int64) error {
	_, err := Client.PutObject(ctx, config.MinIOBucketName, objectName, reader, size, minio.PutObjectOptions{})
	return err
}

func UploadChunkWithEncryption(ctx context.Context, objectName string, reader io.Reader, size int64, keyID string) error {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return err
	}

	_, err = Client.PutObject(ctx, config.MinIOBucketName, objectName, reader, size, minio.PutObjectOptions{
		ServerSideEncryption: sse,
	})
	return err
}

func DownloadFile(ctx context.Context, objectName string) (*minio.Object, error) {
	return Client.GetObject(ctx, config.MinIOBucketName, objectName, minio.GetObjectOptions{})
}

func DownloadFileWithVersion(ctx context.Context, objectName string, versionID string) (*minio.Object, error) {
	opts := minio.GetObjectOptions{}
	if versionID != "" {
		opts.VersionID = versionID
	}
	return Client.GetObject(ctx, config.MinIOBucketName, objectName, opts)
}

func DownloadFileWithEncryption(ctx context.Context, objectName string, keyID string) (*minio.Object, error) {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return nil, err
	}

	opts := minio.GetObjectOptions{
		ServerSideEncryption: sse,
	}
	return Client.GetObject(ctx, config.MinIOBucketName, objectName, opts)
}

func DeleteObject(ctx context.Context, objectName string) error {
	return Client.RemoveObject(ctx, config.MinIOBucketName, objectName, minio.RemoveObjectOptions{})
}

func DeleteObjectVersion(ctx context.Context, objectName string, versionID string) error {
	return Client.RemoveObject(ctx, config.MinIOBucketName, objectName, minio.RemoveObjectOptions{
		VersionID: versionID,
	})
}

func DeleteObjects(ctx context.Context, objectNames []string) error {
	objectsCh := make(chan minio.ObjectInfo, len(objectNames))
	go func() {
		defer close(objectsCh)
		for _, name := range objectNames {
			objectsCh <- minio.ObjectInfo{Key: name}
		}
	}()

	for err := range Client.RemoveObjects(ctx, config.MinIOBucketName, objectsCh, minio.RemoveObjectsOptions{}) {
		if err.Err != nil {
			return err.Err
		}
	}
	return nil
}

func ComposeObject(ctx context.Context, destination string, sources []minio.CopySrcOptions) error {
	_, err := Client.ComposeObject(ctx, minio.ComposeObjectOptions{
		Destination: minio.CopyDestOptions{
			Bucket: config.MinIOBucketName,
			Object: destination,
		},
		Sources: sources,
	})
	return err
}

func ComposeObjectWithEncryption(ctx context.Context, destination string, sources []minio.CopySrcOptions, keyID string) error {
	sse, err := kms.GetMinioEncryption(keyID)
	if err != nil {
		return err
	}

	_, err = Client.ComposeObject(ctx, minio.ComposeObjectOptions{
		Destination: minio.CopyDestOptions{
			Bucket:               config.MinIOBucketName,
			Object:               destination,
			ServerSideEncryption: sse,
		},
		Sources: sources,
	})
	return err
}

func StatObject(ctx context.Context, objectName string) (minio.ObjectInfo, error) {
	return Client.StatObject(ctx, config.MinIOBucketName, objectName, minio.StatObjectOptions{})
}

func StatObjectWithVersion(ctx context.Context, objectName string, versionID string) (minio.ObjectInfo, error) {
	opts := minio.StatObjectOptions{}
	if versionID != "" {
		opts.VersionID = versionID
	}
	return Client.StatObject(ctx, config.MinIOBucketName, objectName, opts)
}

func ListObjectVersions(ctx context.Context, prefix string) ([]minio.ObjectVersion, error) {
	var versions []minio.ObjectVersion

	for object := range Client.ListObjectVersions(ctx, config.MinIOBucketName, prefix, "", "", 1000) {
		if object.Err != nil {
			return nil, object.Err
		}
		versions = append(versions, object)
	}

	return versions, nil
}

func RestoreObjectVersion(ctx context.Context, objectName string, versionID string) error {
	srcOpts := minio.CopySrcOptions{
		Bucket:    config.MinIOBucketName,
		Object:    objectName,
		VersionID: versionID,
	}

	dstOpts := minio.CopyDestOptions{
		Bucket: config.MinIOBucketName,
		Object: objectName,
	}

	_, err := Client.CopyObject(ctx, dstOpts, srcOpts)
	return err
}

func SetLifecycle(ctx context.Context, config *lifecycle.Configuration) error {
	return Client.SetBucketLifecycle(ctx, config.MinIOBucketName, config)
}

func GetLifecycle(ctx context.Context) (*lifecycle.Configuration, error) {
	return Client.GetBucketLifecycle(ctx, config.MinIOBucketName)
}

func SetObjectExpiration(ctx context.Context, objectName string, days int) error {
	config, err := GetLifecycle(ctx)
	if err != nil {
		config = lifecycle.NewConfiguration()
	}

	ruleID := "expire-" + objectName
	config.Rules = append(config.Rules, lifecycle.Rule{
		ID:     ruleID,
		Status: "Enabled",
		Filter: lifecycle.Filter{Prefix: objectName},
		Expiration: lifecycle.Expiration{
			Days: lifecycle.ExpirationDays(days),
		},
	})

	return SetLifecycle(ctx, config)
}

func SetGlobalExpiration(ctx context.Context, days int) error {
	config := lifecycle.NewConfiguration()
	config.Rules = append(config.Rules, lifecycle.Rule{
		ID:     "global-expiration",
		Status: "Enabled",
		Filter: lifecycle.Filter{Prefix: ""},
		Expiration: lifecycle.Expiration{
			Days: lifecycle.ExpirationDays(days),
		},
	})

	return SetLifecycle(ctx, config)
}

func SetNoncurrentVersionExpiration(ctx context.Context, days int) error {
	config, err := GetLifecycle(ctx)
	if err != nil {
		config = lifecycle.NewConfiguration()
	}

	config.Rules = append(config.Rules, lifecycle.Rule{
		ID:     "noncurrent-expiration",
		Status: "Enabled",
		Filter: lifecycle.Filter{Prefix: ""},
		NoncurrentVersionExpiration: lifecycle.NoncurrentVersionExpiration{
			NoncurrentDays: lifecycle.ExpirationDays(days),
		},
	})

	return SetLifecycle(ctx, config)
}

func RemoveLifecycleRule(ctx context.Context, ruleID string) error {
	config, err := GetLifecycle(ctx)
	if err != nil {
		return err
	}

	var newRules []lifecycle.Rule
	for _, rule := range config.Rules {
		if rule.ID != ruleID {
			newRules = append(newRules, rule)
		}
	}
	config.Rules = newRules

	return SetLifecycle(ctx, config)
}

func GetObjectRetention(ctx context.Context, objectName string, versionID string) (*minio.Retention, error) {
	return Client.GetObjectRetention(ctx, config.MinIOBucketName, objectName, versionID)
}

func SetObjectRetention(ctx context.Context, objectName string, versionID string, retention *minio.Retention) error {
	return Client.SetObjectRetention(ctx, config.MinIOBucketName, objectName, versionID, *retention)
}

func CreateObjectLock(ctx context.Context, objectName string, days int) error {
	retention := &minio.Retention{
		Mode:            minio.Governance,
		RetainUntilDate: time.Now().AddDate(0, 0, days),
	}
	return SetObjectRetention(ctx, objectName, "", retention)
}

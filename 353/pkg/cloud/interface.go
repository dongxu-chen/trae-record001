package cloud

import "context"

type CloudProvider interface {
	GetProviderName() string
	GetRegion() string
}

type ComputeProvider interface {
	CloudProvider
	CreateSnapshot(ctx context.Context, instanceID string, snapshotName string) (string, error)
	CreateImageFromSnapshot(ctx context.Context, snapshotID string, imageName string) (string, error)
	ExportImage(ctx context.Context, imageID string, bucketName string, objectKey string) error
	WaitForSnapshotComplete(ctx context.Context, snapshotID string) error
	WaitForImageComplete(ctx context.Context, imageID string) error
}

type DatabaseProvider interface {
	CloudProvider
	CreateDBSnapshot(ctx context.Context, dbInstanceID string, snapshotName string) (string, error)
	ExportDBSnapshotToS3(ctx context.Context, snapshotID string, bucketName string, prefix string) error
	WaitForDBSnapshotComplete(ctx context.Context, snapshotID string) error
}

type StorageProvider interface {
	CloudProvider
	ListObjects(ctx context.Context, bucket string, prefix string) ([]ObjectInfo, error)
	DownloadObject(ctx context.Context, bucket string, key string) ([]byte, error)
	UploadObject(ctx context.Context, bucket string, key string, data []byte) error
	CopyObject(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string) error
	GetObjectMetadata(ctx context.Context, bucket string, key string) (*ObjectInfo, error)
}

type ObjectInfo struct {
	Key          string
	Size         int64
	LastModified int64
	ETag         string
}

type MigrationStatus struct {
	TaskID      string
	Status      string
	Progress    float64
	StartTime   int64
	EndTime     int64
	Message     string
	SourceInfo  map[string]interface{}
	TargetInfo  map[string]interface{}
}

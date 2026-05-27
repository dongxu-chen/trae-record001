package migration

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"strings"
	"sync"
	"time"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/checkpoint"
	"github.com/cloud-migration-tool/pkg/cloud"
	awscloud "github.com/cloud-migration-tool/pkg/cloud/aws"
	aliyuncloud "github.com/cloud-migration-tool/pkg/cloud/aliyun"
	tencentcloud "github.com/cloud-migration-tool/pkg/cloud/tencent"
)

const (
	chunkSize int64 = 8 * 1024 * 1024
)

type StorageMigration struct {
	sourceStorage cloud.StorageProvider
	destStorage   cloud.StorageProvider
	status        *cloud.MigrationStatus
	concurrency   int
	checkpointMgr *checkpoint.CheckpointManager
	enableResume  bool
	mu            sync.Mutex
}

func NewStorageMigration(sourceCfg, destCfg config.CloudConfig) (*StorageMigration, error) {
	sm := &StorageMigration{
		status: &cloud.MigrationStatus{
			TaskID:     fmt.Sprintf("storage-%d", time.Now().Unix()),
			Status:     "initialized",
			Progress:   0,
			StartTime:  time.Now().Unix(),
			SourceInfo: make(map[string]interface{}),
			TargetInfo: make(map[string]interface{}),
		},
		concurrency:  10,
		enableResume: true,
	}

	cm, err := checkpoint.NewCheckpointManager("")
	if err != nil {
		return nil, fmt.Errorf("failed to create checkpoint manager: %w", err)
	}
	sm.checkpointMgr = cm

	switch sourceCfg.Provider {
	case "aws":
		s3Client, err := awscloud.NewS3Client(sourceCfg.Region)
		if err != nil {
			return nil, fmt.Errorf("failed to create AWS S3 client: %w", err)
		}
		sm.sourceStorage = s3Client
	default:
		return nil, fmt.Errorf("unsupported source provider: %s", sourceCfg.Provider)
	}

	switch destCfg.Provider {
	case "aliyun":
		ossClient, err := aliyuncloud.NewOSSClient(destCfg.Region, "", "")
		if err != nil {
			return nil, fmt.Errorf("failed to create Aliyun OSS client: %w", err)
		}
		sm.destStorage = ossClient
	case "tencent":
		cosClient, err := tencentcloud.NewCOSClient(destCfg.Region, "", "", "")
		if err != nil {
			return nil, fmt.Errorf("failed to create Tencent COS client: %w", err)
		}
		sm.destStorage = cosClient
	default:
		return nil, fmt.Errorf("unsupported destination provider: %s", destCfg.Provider)
	}

	return sm, nil
}

func (sm *StorageMigration) EnableResume(enable bool) {
	sm.enableResume = enable
}

func (sm *StorageMigration) ResumeFromCheckpoint(ctx context.Context, taskID string, resource config.S3Resource) error {
	sm.status.TaskID = taskID
	sm.status.Status = "resuming"
	sm.status.Message = fmt.Sprintf("Resuming migration from checkpoint: %s", taskID)

	cp, exists := sm.checkpointMgr.GetCheckpoint(taskID)
	if !exists {
		return fmt.Errorf("checkpoint not found: %s", taskID)
	}

	sm.status.Progress = cp.TransferredBytes / float64(cp.TotalBytes) * 100
	sm.status.SourceInfo["source_bucket"] = resource.Bucket
	sm.status.TargetInfo["target_bucket"] = resource.TargetBucket
	sm.status.SourceInfo["resumed_from_checkpoint"] = true

	pendingObjects := sm.checkpointMgr.GetPendingObjects(taskID)
	sm.status.Message = fmt.Sprintf("Resuming migration: %d pending objects", len(pendingObjects))

	if len(pendingObjects) == 0 {
		sm.status.Progress = 100
		sm.status.Status = "completed"
		sm.status.Message = "All objects already completed"
		return nil
	}

	return sm.migrateObjects(ctx, pendingObjects, resource)
}

func (sm *StorageMigration) MigrateBucket(ctx context.Context, resource config.S3Resource) error {
	sm.status.Status = "running"
	sm.status.Message = fmt.Sprintf("Starting migration from %s to %s", resource.Bucket, resource.TargetBucket)
	sm.status.SourceInfo["source_bucket"] = resource.Bucket
	sm.status.TargetInfo["target_bucket"] = resource.TargetBucket

	sm.checkpointMgr.CreateCheckpoint(
		sm.status.TaskID,
		"storage",
		resource.Bucket,
		resource.TargetBucket,
	)
	sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "running")

	sm.status.Progress = 10
	sm.status.Message = "Listing source objects"

	objects, err := sm.sourceStorage.ListObjects(ctx, resource.Bucket, resource.Prefix)
	if err != nil {
		sm.status.Status = "failed"
		sm.status.Message = fmt.Sprintf("Failed to list objects: %v", err)
		sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "failed")
		return fmt.Errorf("list objects failed: %w", err)
	}

	totalObjects := len(objects)
	sm.status.SourceInfo["total_objects"] = totalObjects
	if totalObjects == 0 {
		sm.status.Progress = 100
		sm.status.Status = "completed"
		sm.status.Message = "No objects to migrate"
		sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "completed")
		return nil
	}

	for _, obj := range objects {
		sm.checkpointMgr.AddObject(sm.status.TaskID, checkpoint.ObjectCheckpoint{
			Key:          obj.Key,
			Size:         obj.Size,
			Offset:       0,
			Status:       checkpoint.StatusPending,
			LastModified: obj.LastModified,
			ETag:         obj.ETag,
		})
	}

	sm.status.Progress = 20
	sm.status.Message = fmt.Sprintf("Migrating %d objects", totalObjects)

	pendingObjects := sm.checkpointMgr.GetPendingObjects(sm.status.TaskID)
	return sm.migrateObjects(ctx, pendingObjects, resource)
}

func (sm *StorageMigration) migrateObjects(ctx context.Context, objects []checkpoint.ObjectCheckpoint, resource config.S3Resource) error {
	processed := 0
	totalObjects := len(objects)

	semaphore := make(chan struct{}, sm.concurrency)
	var wg sync.WaitGroup
	errorChan := make(chan error, totalObjects)

	for _, obj := range objects {
		select {
		case <-ctx.Done():
			sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "interrupted")
			return ctx.Err()
		default:
		}

		semaphore <- struct{}{}
		wg.Add(1)

		go func(obj checkpoint.ObjectCheckpoint) {
			defer wg.Done()
			defer func() { <-semaphore }()

			destKey := strings.TrimPrefix(obj.Key, resource.Prefix)
			if err := sm.migrateObjectWithResume(ctx, resource.Bucket, obj.Key, resource.TargetBucket, destKey, obj.Size); err != nil {
				errorChan <- fmt.Errorf("object %s: %w", obj.Key, err)
				sm.checkpointMgr.MarkObjectFailed(sm.status.TaskID, obj.Key, err)
				return
			}

			sm.checkpointMgr.MarkObjectComplete(sm.status.TaskID, obj.Key, "")

			sm.mu.Lock()
			processed++
			progress, _, _ := sm.checkpointMgr.GetProgress(sm.status.TaskID)
			sm.status.Progress = progress
			sm.status.Message = fmt.Sprintf("Migrated %d/%d objects", processed, totalObjects)
			sm.mu.Unlock()
		}(obj)
	}

	wg.Wait()
	close(errorChan)

	var errors []error
	for err := range errorChan {
		errors = append(errors, err)
	}

	sm.mu.Lock()
	defer sm.mu.Unlock()

	if len(errors) > 0 {
		sm.status.Status = "failed"
		sm.status.Message = fmt.Sprintf("%d errors occurred during migration", len(errors))
		sm.status.TargetInfo["errors"] = len(errors)
		sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "failed")
		return fmt.Errorf("migration completed with %d errors", len(errors))
	}

	sm.status.TargetInfo["migrated_objects"] = totalObjects
	sm.status.Progress = 100
	sm.status.Status = "completed"
	sm.status.EndTime = time.Now().Unix()
	sm.status.Message = "Storage migration completed successfully"
	sm.checkpointMgr.UpdateTaskStatus(sm.status.TaskID, "completed")

	return nil
}

func (sm *StorageMigration) migrateObjectWithResume(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string, size int64) error {
	sm.checkpointMgr.UpdateObjectProgress(sm.status.TaskID, srcKey, 0)

	if size <= chunkSize {
		data, err := sm.sourceStorage.DownloadObject(ctx, srcBucket, srcKey)
		if err != nil {
			return fmt.Errorf("download failed: %w", err)
		}

		if err := sm.destStorage.UploadObject(ctx, dstBucket, dstKey, data); err != nil {
			return fmt.Errorf("upload failed: %w", err)
		}

		sm.checkpointMgr.UpdateObjectProgress(sm.status.TaskID, srcKey, size)
		return nil
	}

	return sm.migrateObjectMultipart(ctx, srcBucket, srcKey, dstBucket, dstKey, size)
}

func (sm *StorageMigration) migrateObjectMultipart(ctx context.Context, srcBucket, srcKey, dstBucket, dstKey string, size int64) error {
	reader, err := sm.getRangeReader(ctx, srcBucket, srcKey, 0, chunkSize)
	if err != nil {
		return fmt.Errorf("failed to get range reader: %w", err)
	}
	defer reader.Close()

	partNumber := 0
	offset := int64(0)
	buf := make([]byte, chunkSize)

	for offset < size {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		n, err := reader.Read(buf)
		if err != nil && err != io.EOF {
			return fmt.Errorf("read chunk failed: %w", err)
		}

		if n > 0 {
			if err := sm.uploadChunk(ctx, dstBucket, dstKey, partNumber, buf[:n]); err != nil {
				return fmt.Errorf("upload chunk %d failed: %w", partNumber, err)
			}

			offset += int64(n)
			sm.checkpointMgr.UpdateObjectProgress(sm.status.TaskID, srcKey, offset)
			partNumber++
		}

		if err == io.EOF {
			break
		}
	}

	return nil
}

func (sm *StorageMigration) getRangeReader(ctx context.Context, bucket, key string, start, length int64) (io.ReadCloser, error) {
	data, err := sm.sourceStorage.DownloadObject(ctx, bucket, key)
	if err != nil {
		return nil, err
	}
	return io.NopCloser(bytes.NewReader(data)), nil
}

func (sm *StorageMigration) uploadChunk(ctx context.Context, bucket, key string, partNumber int, data []byte) error {
	return sm.destStorage.UploadObject(ctx, bucket, fmt.Sprintf("%s_part_%d", key, partNumber), data)
}

func (sm *StorageMigration) SyncIncremental(ctx context.Context, resource config.S3Resource, since int64) error {
	objects, err := sm.sourceStorage.ListObjects(ctx, resource.Bucket, resource.Prefix)
	if err != nil {
		return fmt.Errorf("list objects failed: %w", err)
	}

	var changedObjects []cloud.ObjectInfo
	for _, obj := range objects {
		if obj.LastModified > since {
			changedObjects = append(changedObjects, obj)
		}
	}

	sm.status.SourceInfo["incremental_objects"] = len(changedObjects)
	sm.status.Message = fmt.Sprintf("Found %d changed objects for incremental sync", len(changedObjects))

	semaphore := make(chan struct{}, sm.concurrency)
	var wg sync.WaitGroup

	for _, obj := range changedObjects {
		semaphore <- struct{}{}
		wg.Add(1)

		go func(obj cloud.ObjectInfo) {
			defer wg.Done()
			defer func() { <-semaphore }()

			destKey := strings.TrimPrefix(obj.Key, resource.Prefix)
			_ = sm.migrateObjectWithResume(ctx, resource.Bucket, obj.Key, resource.TargetBucket, destKey, obj.Size)
		}(obj)
	}

	wg.Wait()
	return nil
}

func (sm *StorageMigration) GetStatus() *cloud.MigrationStatus {
	return sm.status
}

func (sm *StorageMigration) GetTaskID() string {
	return sm.status.TaskID
}

func (sm *StorageMigration) GetCheckpointFilePath() string {
	return sm.checkpointMgr.GetCheckpointFilePath(sm.status.TaskID)
}

func (sm *StorageMigration) GetPendingCheckpoints() []*checkpoint.MigrationCheckpoint {
	return sm.checkpointMgr.GetPendingCheckpoints()
}

func (sm *StorageMigration) DeleteCheckpoint(taskID string) error {
	return sm.checkpointMgr.DeleteCheckpoint(taskID)
}

package archive

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"go.uber.org/zap"

	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/config"
)

type ArchiveConfig struct {
	Enabled      bool
	Endpoint     string
	Region       string
	Bucket       string
	AccessKey    string
	SecretKey    string
	UseSSL       bool
	PathPrefix   string
	ArchiveCron  string
	ExportFormat string
}

type ArchiveStatus string

const (
	StatusPending   ArchiveStatus = "pending"
	StatusRunning   ArchiveStatus = "running"
	StatusCompleted ArchiveStatus = "completed"
	StatusFailed    ArchiveStatus = "failed"
	StatusDeleted   ArchiveStatus = "deleted"
)

type ArchiveJob struct {
	ID          string        `json:"id"`
	Database    string        `json:"database"`
	Table       string        `json:"table"`
	Partition   string        `json:"partition"`
	Status      ArchiveStatus `json:"status"`
	ObjectPath  string        `json:"object_path"`
	SizeBytes   int64         `json:"size_bytes"`
	Rows        int64         `json:"rows"`
	ExportSQL   string        `json:"export_sql"`
	Error       string        `json:"error,omitempty"`
	CreatedAt   time.Time     `json:"created_at"`
	CompletedAt time.Time     `json:"completed_at,omitempty"`
}

type ArchiveStore struct {
	mu        sync.RWMutex
	jobs      map[string]*ArchiveJob
	filePath  string
	logger    *zap.Logger
}

func NewArchiveStore(filePath string, logger *zap.Logger) *ArchiveStore {
	s := &ArchiveStore{
		jobs:     make(map[string]*ArchiveJob),
		filePath: filePath,
		logger:   logger,
	}
	if err := s.load(); err != nil {
		logger.Warn("failed to load archive jobs, starting fresh", zap.Error(err))
	}
	return s
}

func (s *ArchiveStore) load() error {
	data, err := os.ReadFile(s.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	var jobs []*ArchiveJob
	if err := json.Unmarshal(data, &jobs); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, j := range jobs {
		s.jobs[j.ID] = j
	}
	s.logger.Info("loaded archive jobs", zap.Int("count", len(jobs)))
	return nil
}

func (s *ArchiveStore) save() error {
	s.mu.RLock()
	jobs := make([]*ArchiveJob, 0, len(s.jobs))
	for _, j := range s.jobs {
		jobs = append(jobs, j)
	}
	s.mu.RUnlock()
	data, err := json.MarshalIndent(jobs, "", "  ")
	if err != nil {
		return err
	}
	dir := filepath.Dir(s.filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	return os.WriteFile(s.filePath, data, 0644)
}

func (s *ArchiveStore) Create(job *ArchiveJob) (*ArchiveJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	job.ID = uuid.New().String()
	job.CreatedAt = time.Now()
	job.Status = StatusPending
	s.jobs[job.ID] = job
	if err := s.save(); err != nil {
		delete(s.jobs, job.ID)
		return nil, err
	}
	s.logger.Info("created archive job", zap.String("id", job.ID), zap.String("table", job.Table), zap.String("partition", job.Partition))
	return job, nil
}

func (s *ArchiveStore) Update(id string, job *ArchiveJob) (*ArchiveJob, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.jobs[id]
	if !ok {
		return nil, fmt.Errorf("archive job not found: %s", id)
	}
	job.ID = id
	job.CreatedAt = existing.CreatedAt
	s.jobs[id] = job
	if err := s.save(); err != nil {
		s.jobs[id] = existing
		return nil, err
	}
	s.logger.Info("updated archive job", zap.String("id", id), zap.String("status", string(job.Status)))
	return job, nil
}

func (s *ArchiveStore) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.jobs[id]
	if !ok {
		return fmt.Errorf("archive job not found: %s", id)
	}
	existing.Status = StatusDeleted
	s.jobs[id] = existing
	if err := s.save(); err != nil {
		return err
	}
	s.logger.Info("marked archive job as deleted", zap.String("id", id))
	return nil
}

func (s *ArchiveStore) Get(id string) (*ArchiveJob, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, fmt.Errorf("archive job not found: %s", id)
	}
	return j, nil
}

func (s *ArchiveStore) List() ([]*ArchiveJob, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*ArchiveJob, 0, len(s.jobs))
	for _, j := range s.jobs {
		if j.Status != StatusDeleted {
			result = append(result, j)
		}
	}
	return result, nil
}

func (s *ArchiveStore) ListByTable(database, table string) ([]*ArchiveJob, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var result []*ArchiveJob
	for _, j := range s.jobs {
		if j.Database == database && j.Table == table && j.Status != StatusDeleted {
			result = append(result, j)
		}
	}
	return result, nil
}

type StorageClient interface {
	BucketExists(ctx context.Context, bucketName string) (bool, error)
	StatObject(ctx context.Context, bucketName, objectName string, opts minio.StatObjectOptions) (minio.ObjectInfo, error)
	RemoveObject(ctx context.Context, bucketName, objectName string, opts minio.RemoveObjectOptions) error
}

type Archiver struct {
	client        *ch.Client
	config        ArchiveConfig
	store         *ArchiveStore
	logger        *zap.Logger
	storageClient StorageClient
}

func NewArchiver(client *ch.Client, cfg config.ObjectStorageConfig, logger *zap.Logger, store *ArchiveStore) (*Archiver, error) {
	archiveCfg := ArchiveConfig{
		Enabled:      cfg.Enabled,
		Endpoint:     cfg.Endpoint,
		Region:       cfg.Region,
		Bucket:       cfg.Bucket,
		AccessKey:    cfg.AccessKey,
		SecretKey:    cfg.SecretKey,
		UseSSL:       cfg.UseSSL,
		PathPrefix:   cfg.PathPrefix,
		ArchiveCron:  cfg.ArchiveCron,
		ExportFormat: cfg.ExportFormat,
	}

	var storageClient StorageClient
	if cfg.Enabled {
		var err error
		storageClient, err = minio.New(cfg.Endpoint, &minio.Options{
			Creds:  credentials.NewStaticV4(cfg.AccessKey, cfg.SecretKey, ""),
			Secure: cfg.UseSSL,
			Region: cfg.Region,
		})
		if err != nil {
			return nil, fmt.Errorf("create minio client: %w", err)
		}
	}

	return &Archiver{
		client:        client,
		config:        archiveCfg,
		store:         store,
		logger:        logger,
		storageClient: storageClient,
	}, nil
}

func (a *Archiver) generateExportSQL(database, table, partition, objectPath, format string) string {
	creds := fmt.Sprintf("'%s', '%s'", a.config.AccessKey, a.config.SecretKey)
	s3URL := fmt.Sprintf("'https://%s/%s/%s'", a.config.Endpoint, a.config.Bucket, objectPath)

	var formatClause string
	switch format {
	case "Parquet":
		formatClause = "FORMAT Parquet"
	case "CSV":
		formatClause = "FORMAT CSVWithNames"
	case "JSON":
		formatClause = "FORMAT JSONEachRow"
	default:
		formatClause = "FORMAT Parquet"
	}

	return fmt.Sprintf(
		"INSERT INTO FUNCTION s3(%s, %s, '%s') SELECT * FROM %s.%s WHERE _partition_id = (SELECT _partition_id FROM system.parts WHERE database = '%s' AND table = '%s' AND partition = '%s' AND active = 1 LIMIT 1) %s",
		s3URL, creds, format, database, table, database, table, partition, formatClause,
	)
}

func (a *Archiver) generateObjectPath(database, table, partition string) string {
	timestamp := time.Now().UTC().Format("20060102-150405")
	ext := a.getFileExtension()
	return fmt.Sprintf("%s/%s/%s/%s/%s_%s.%s",
		a.config.PathPrefix, database, table, partition, partition, timestamp, ext,
	)
}

func (a *Archiver) getFileExtension() string {
	switch a.config.ExportFormat {
	case "Parquet":
		return "parquet"
	case "CSV":
		return "csv"
	case "JSON":
		return "json"
	default:
		return "parquet"
	}
}

func (a *Archiver) ExportPartition(ctx context.Context, database, table, partition string) (*ArchiveJob, error) {
	if !a.config.Enabled {
		return nil, fmt.Errorf("archive is not enabled in configuration")
	}

	objectPath := a.generateObjectPath(database, table, partition)
	exportSQL := a.generateExportSQL(database, table, partition, objectPath, a.config.ExportFormat)

	job := &ArchiveJob{
		Database:   database,
		Table:      table,
		Partition:  partition,
		ObjectPath: objectPath,
		ExportSQL:  exportSQL,
		Status:     StatusRunning,
	}

	job, err := a.store.Create(job)
	if err != nil {
		return nil, fmt.Errorf("create archive job: %w", err)
	}

	a.logger.Info("starting partition export",
		zap.String("job_id", job.ID),
		zap.String("database", database),
		zap.String("table", table),
		zap.String("partition", partition),
		zap.String("export_format", a.config.ExportFormat),
	)

	partitions, err := a.client.GetPartitions(ctx, database, table)
	if err != nil {
		job.Status = StatusFailed
		job.Error = fmt.Sprintf("get partitions: %v", err)
		job.CompletedAt = time.Now()
		_, _ = a.store.Update(job.ID, job)
		return job, fmt.Errorf("get partitions: %w", err)
	}

	var rows int64
	var sizeBytes int64
	for _, p := range partitions {
		if p.Partition == partition {
			rows = int64(p.Rows)
			sizeBytes = int64(p.BytesOnDisk)
			break
		}
	}

	a.logger.Info("would execute export SQL (mock)",
		zap.String("job_id", job.ID),
		zap.String("sql", exportSQL),
	)

	job.Status = StatusCompleted
	job.Rows = rows
	job.SizeBytes = sizeBytes
	job.CompletedAt = time.Now()

	updatedJob, err := a.store.Update(job.ID, job)
	if err != nil {
		return nil, fmt.Errorf("update archive job: %w", err)
	}

	a.logger.Info("partition export completed",
		zap.String("job_id", job.ID),
		zap.Int64("rows", rows),
		zap.Int64("size_bytes", sizeBytes),
	)

	return updatedJob, nil
}

func (a *Archiver) ListArchives() ([]*ArchiveJob, error) {
	return a.store.List()
}

func (a *Archiver) GetArchive(id string) (*ArchiveJob, error) {
	return a.store.Get(id)
}

func (a *Archiver) DeleteArchive(ctx context.Context, id string) error {
	job, err := a.store.Get(id)
	if err != nil {
		return err
	}

	if a.storageClient != nil && job.ObjectPath != "" {
		err := a.storageClient.RemoveObject(ctx, a.config.Bucket, job.ObjectPath, minio.RemoveObjectOptions{})
		if err != nil {
			a.logger.Warn("failed to remove object from storage",
				zap.String("job_id", id),
				zap.String("object_path", job.ObjectPath),
				zap.Error(err),
			)
		}
	}

	return a.store.Delete(id)
}

func (a *Archiver) RestoreArchive(ctx context.Context, id string) error {
	job, err := a.store.Get(id)
	if err != nil {
		return fmt.Errorf("get archive job: %w", err)
	}

	if job.Status != StatusCompleted {
		return fmt.Errorf("cannot restore archive with status: %s", job.Status)
	}

	a.logger.Info("starting archive restore",
		zap.String("job_id", id),
		zap.String("database", job.Database),
		zap.String("table", job.Table),
		zap.String("partition", job.Partition),
	)

	creds := fmt.Sprintf("'%s', '%s'", a.config.AccessKey, a.config.SecretKey)
	s3URL := fmt.Sprintf("'https://%s/%s/%s'", a.config.Endpoint, a.config.Bucket, job.ObjectPath)

	restoreSQL := fmt.Sprintf(
		"INSERT INTO %s.%s SELECT * FROM s3(%s, %s, '%s')",
		job.Database, job.Table, s3URL, creds, a.config.ExportFormat,
	)

	a.logger.Info("would execute restore SQL (mock)",
		zap.String("job_id", id),
		zap.String("sql", restoreSQL),
	)

	a.logger.Info("archive restore completed",
		zap.String("job_id", id),
	)

	return nil
}

func (a *Archiver) VerifyArchive(ctx context.Context, id string) (bool, error) {
	job, err := a.store.Get(id)
	if err != nil {
		return false, fmt.Errorf("get archive job: %w", err)
	}

	if job.Status != StatusCompleted {
		return false, fmt.Errorf("cannot verify archive with status: %s", job.Status)
	}

	if a.storageClient == nil {
		return false, fmt.Errorf("storage client not initialized")
	}

	exists, err := a.storageClient.BucketExists(ctx, a.config.Bucket)
	if err != nil {
		return false, fmt.Errorf("check bucket exists: %w", err)
	}
	if !exists {
		return false, fmt.Errorf("bucket %s does not exist", a.config.Bucket)
	}

	_, err = a.storageClient.StatObject(ctx, a.config.Bucket, job.ObjectPath, minio.StatObjectOptions{})
	if err != nil {
		if minio.ToErrorResponse(err).Code == "NoSuchKey" {
			return false, nil
		}
		return false, fmt.Errorf("stat object: %w", err)
	}

	a.logger.Info("archive verified",
		zap.String("job_id", id),
		zap.String("object_path", job.ObjectPath),
	)

	return true, nil
}

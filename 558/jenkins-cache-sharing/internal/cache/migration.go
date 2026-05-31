package cache

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/jenkins-cache-sharing/internal/config"
	"github.com/jenkins-cache-sharing/internal/model"
	"github.com/jenkins-cache-sharing/internal/storage"
	"go.uber.org/zap"
)

type StorageBackend struct {
	ID        string
	Name      string
	Storage   *storage.ObjectStorage
	Config    config.StorageBackendConfig
	IsDefault bool
	IsActive  bool
}

type MigrationEngine struct {
	meta      *MetaStore
	backends  map[string]*StorageBackend
	tasks     map[string]*model.MigrationTask
	progress  map[string]*model.MigrationProgress
	defaultID string
	mu        sync.RWMutex
	taskMu    sync.Mutex
	logger    *zap.Logger
}

func NewMigrationEngine(meta *MetaStore, defaultStorage *storage.ObjectStorage, defaultConfig config.StorageConfig, logger *zap.Logger) *MigrationEngine {
	defaultBackend := &StorageBackend{
		ID:        "default",
		Name:      "Default Storage",
		Storage:   defaultStorage,
		IsDefault: true,
		IsActive:  true,
		Config: config.StorageBackendConfig{
			ID:       "default",
			Name:     "Default Storage",
			Endpoint: defaultConfig.Endpoint,
			AccessKey: defaultConfig.AccessKey,
			SecretKey: defaultConfig.SecretKey,
			Bucket:   defaultConfig.Bucket,
			Region:   defaultConfig.Region,
			UseSSL:   defaultConfig.UseSSL,
			IsDefault: true,
		},
	}

	return &MigrationEngine{
		meta:      meta,
		backends:  map[string]*StorageBackend{"default": defaultBackend},
		tasks:     make(map[string]*model.MigrationTask),
		progress:  make(map[string]*model.MigrationProgress),
		defaultID: "default",
		logger:    logger,
	}
}

func (me *MigrationEngine) AddBackend(ctx context.Context, cfg config.StorageBackendConfig) (*StorageBackend, error) {
	me.mu.Lock()
	defer me.mu.Unlock()

	if cfg.ID == "" {
		cfg.ID = generateID()
	}

	objStorage, err := storage.NewObjectStorage(config.StorageConfig{
		Endpoint: cfg.Endpoint,
		AccessKey: cfg.AccessKey,
		SecretKey: cfg.SecretKey,
		Bucket: cfg.Bucket,
		Region: cfg.Region,
		UseSSL: cfg.UseSSL,
	}, me.logger)
	if err != nil {
		return nil, fmt.Errorf("failed to create object storage: %w", err)
	}

	backend := &StorageBackend{
		ID:        cfg.ID,
		Name:      cfg.Name,
		Storage:   objStorage,
		Config:    cfg,
		IsDefault: cfg.IsDefault,
		IsActive:  true,
	}

	me.backends[cfg.ID] = backend

	if cfg.IsDefault {
		for id, b := range me.backends {
			if id != cfg.ID {
				b.IsDefault = false
			}
		}
		me.defaultID = cfg.ID
	}

	me.logger.Info("added storage backend",
		zap.String("id", cfg.ID),
		zap.String("name", cfg.Name),
		zap.String("endpoint", cfg.Endpoint),
	)

	return backend, nil
}

func (me *MigrationEngine) RemoveBackend(ctx context.Context, backendID string) error {
	me.mu.Lock()
	defer me.mu.Unlock()

	if backendID == me.defaultID {
		return fmt.Errorf("cannot remove default backend")
	}

	delete(me.backends, backendID)
	me.logger.Info("removed storage backend", zap.String("id", backendID))
	return nil
}

func (me *MigrationEngine) GetBackend(backendID string) (*StorageBackend, error) {
	me.mu.RLock()
	defer me.mu.RUnlock()

	backend, ok := me.backends[backendID]
	if !ok {
		return nil, fmt.Errorf("backend not found: %s", backendID)
	}
	return backend, nil
}

func (me *MigrationEngine) ListBackends(ctx context.Context) ([]*model.StorageBackend, error) {
	me.mu.RLock()
	defer me.mu.RUnlock()

	var result []*model.StorageBackend
	for _, b := range me.backends {
		result = append(result, &model.StorageBackend{
			ID: b.ID,
			Name: b.Name,
			Type: b.Config.Type,
			Endpoint: b.Config.Endpoint,
			Bucket: b.Config.Bucket,
			Region: b.Config.Region,
			IsDefault: b.IsDefault,
			IsActive: b.IsActive,
		})
	}
	return result, nil
}

func (me *MigrationEngine) GetDefaultBackend() *StorageBackend {
	me.mu.RLock()
	defer me.mu.RUnlock()

	return me.backends[me.defaultID]
}

func (me *MigrationEngine) CreateMigrationTask(
	ctx context.Context,
	name string,
	sourceID, targetID string,
	mode model.MigrationMode,
	cacheTypes []model.CacheType,
	jobNames []string,
	entryIDs []string,
	deleteSource bool,
) (*model.MigrationTask, error) {
	me.taskMu.Lock()
	defer me.taskMu.Unlock()

	_, err := me.GetBackend(sourceID)
	if err != nil {
		return nil, fmt.Errorf("invalid source backend: %w", err)
	}

	_, err = me.GetBackend(targetID)
	if err != nil {
		return nil, fmt.Errorf("invalid target backend: %w", err)
	}

	task := &model.MigrationTask{
		ID:              generateID(),
		Name:            name,
		SourceBackendID: sourceID,
		TargetBackendID: targetID,
		Mode:            mode,
		Status:          model.MigrationStatusPending,
		CacheTypes:      cacheTypes,
		JobNames:        jobNames,
		EntryIDs:        entryIDs,
		DeleteSource:    deleteSource,
		CreatedAt:       time.Now(),
	}

	me.mu.Lock()
	me.tasks[task.ID] = task
	me.mu.Unlock()

	me.logger.Info("created migration task",
		zap.String("id", task.ID),
		zap.String("name", name),
		zap.String("source", sourceID),
		zap.String("target", targetID),
		zap.String("mode", string(mode)),
	)

	return task, nil
}

func (me *MigrationEngine) StartMigration(ctx context.Context, taskID string) (*model.MigrationTask, error) {
	me.taskMu.Lock()
	defer me.taskMu.Unlock()

	me.mu.Lock()
	task, ok := me.tasks[taskID]
	me.mu.Unlock()

	if !ok {
		return nil, fmt.Errorf("task not found: %s", taskID)
	}

	if task.Status == model.MigrationStatusRunning {
		return nil, fmt.Errorf("task already running")
	}

	source, _ := me.GetBackend(task.SourceBackendID)
	target, _ := me.GetBackend(task.TargetBackendID)

	me.meta.mu.RLock()
	var entriesToMigrate []*model.CacheEntry
	for _, entry := range me.meta.entries {
		if entry.Status != model.CacheStatusActive {
			continue
		}

		if task.CacheTypes != nil && len(task.CacheTypes) > 0 {
			matched := false
			for _, t := range task.CacheTypes {
				if t == entry.Type {
					matched = true
					break
				}
			}
			if !matched {
				continue
			}
		}

		if task.JobNames != nil && len(task.JobNames) > 0 {
			matched := false
			for _, j := range task.JobNames {
				if j == entry.JobName {
					matched = true
					break
				}
			}
			if !matched {
				continue
			}
		}

		if task.EntryIDs != nil && len(task.EntryIDs) > 0 {
			matched := false
			for _, id := range task.EntryIDs {
				if id == entry.ID {
					matched = true
					break
				}
			}
			if !matched {
				continue
			}
		}

		if task.Mode == model.MigrationModeIncremental {
			_, statErr := target.Storage.Download(ctx, entry.ObjectKey)
			if statErr == nil {
				continue
			}
		}

		entriesToMigrate = append(entriesToMigrate, entry)
	}
	me.meta.mu.RUnlock()

	totalSize := int64(0)
	for _, e := range entriesToMigrate {
		totalSize += e.Size
	}

	task.TotalCount = len(entriesToMigrate)
	task.TotalSize = totalSize
	task.Status = model.MigrationStatusRunning
	now := time.Now()
	task.StartedAt = &now

	me.mu.Lock()
	me.tasks[taskID] = task
	me.progress[taskID] = &model.MigrationProgress{
		TaskID:        taskID,
		TotalCount:    task.TotalCount,
		TotalSize:     task.TotalSize,
		CompletedCount: 0,
		CompletedSize: 0,
		Progress:     0,
	}
	me.mu.Unlock()

	go me.executeMigration(ctx, task, entriesToMigrate, source, target)

	me.logger.Info("started migration",
		zap.String("task_id", taskID),
		zap.Int("total_entries", task.TotalCount),
		zap.Int64("total_size", task.TotalSize),
	)

	return task, nil
}

func (me *MigrationEngine) executeMigration(
	ctx context.Context,
	task *model.MigrationTask,
	entries []*model.CacheEntry,
	source, target *StorageBackend,
) {
	for _, entry := range entries {
		me.mu.Lock()
		progress := me.progress[task.ID]
		progress.CurrentEntry = entry.ID
		progress.CurrentJob = entry.JobName
		me.mu.Unlock()

		err := me.migrateEntry(ctx, entry, source, target, task.DeleteSource)
		if err != nil {
			me.logger.Error("failed to migrate entry",
				zap.String("entry_id", entry.ID),
				zap.Error(err),
			)
			me.mu.Lock()
			task.FailedCount++
			me.tasks[task.ID] = task
			me.mu.Unlock()
			continue
		}

		me.mu.Lock()
		task.CompletedCount++
		task.CompletedSize += entry.Size
		if task.TotalCount > 0 {
			task.Progress = float64(task.CompletedCount) / float64(task.TotalCount) * 100
		}

		progress := me.progress[task.ID]
		progress.CompletedCount = task.CompletedCount
		progress.CompletedSize = task.CompletedSize
		progress.Progress = task.Progress

		me.tasks[task.ID] = task
		me.mu.Unlock()
	}

	me.mu.Lock()
	task.Status = model.MigrationStatusCompleted
	now := time.Now()
	task.FinishedAt = &now
	me.tasks[task.ID] = task
	me.mu.Unlock()

	me.logger.Info("migration completed",
		zap.String("task_id", task.ID),
		zap.Int("completed", task.CompletedCount),
		zap.Int("failed", task.FailedCount),
		zap.Int64("size", task.CompletedSize),
	)
}

func (me *MigrationEngine) migrateEntry(
	ctx context.Context,
	entry *model.CacheEntry,
	source, target *StorageBackend,
	deleteSource bool,
) error {
	reader, size, err := source.Storage.Download(ctx, entry.ObjectKey)
	if err != nil {
		return fmt.Errorf("failed to download from source: %w", err)
	}
	defer reader.Close()

	_, err = target.Storage.Upload(ctx, entry.Type, entry.JobName, entry.BuildNumber, reader, size, entry.Version)
	if err != nil {
		return fmt.Errorf("failed to upload to target: %w", err)
	}

	if deleteSource {
		if err := source.Storage.Delete(ctx, entry.ObjectKey); err != nil {
			me.logger.Warn("failed to delete from source after migration",
				zap.String("entry_id", entry.ID),
				zap.Error(err),
			)
		}
	}

	return nil
}

func (me *MigrationEngine) GetTask(ctx context.Context, taskID string) (*model.MigrationTask, error) {
	me.mu.RLock()
	defer me.mu.RUnlock()

	task, ok := me.tasks[taskID]
	if !ok {
		return nil, fmt.Errorf("task not found: %s", taskID)
	}
	return task, nil
}

func (me *MigrationEngine) ListTasks(ctx context.Context) ([]*model.MigrationTask, error) {
	me.mu.RLock()
	defer me.mu.RUnlock()

	var tasks []*model.MigrationTask
	for _, t := range me.tasks {
		tasks = append(tasks, t)
	}
	return tasks, nil
}

func (me *MigrationEngine) GetProgress(ctx context.Context, taskID string) (*model.MigrationProgress, error) {
	me.mu.RLock()
	defer me.mu.RUnlock()

	progress, ok := me.progress[taskID]
	if !ok {
		return nil, fmt.Errorf("task not found: %s", taskID)
	}
	return progress, nil
}

func (me *MigrationEngine) PauseMigration(ctx context.Context, taskID string) error {
	me.mu.Lock()
	defer me.mu.Unlock()

	task, ok := me.tasks[taskID]
	if !ok {
		return fmt.Errorf("task not found: %s", taskID)
	}

	if task.Status != model.MigrationStatusRunning {
		return fmt.Errorf("task is not running")
	}

	task.Status = model.MigrationStatusPaused
	me.tasks[taskID] = task

	me.logger.Info("migration paused", zap.String("task_id", taskID))
	return nil
}

func (me *MigrationEngine) ResumeMigration(ctx context.Context, taskID string) error {
	me.mu.Lock()
	defer me.mu.Unlock()

	task, ok := me.tasks[taskID]
	if !ok {
		return fmt.Errorf("task not found: %s", taskID)
	}

	if task.Status != model.MigrationStatusPaused {
		return fmt.Errorf("task is not paused")
	}

	task.Status = model.MigrationStatusRunning
	me.tasks[taskID] = task

	me.logger.Info("migration resumed", zap.String("task_id", taskID))
	return nil
}

func (me *MigrationEngine) CancelMigration(ctx context.Context, taskID string) error {
	me.mu.Lock()
	defer me.mu.Unlock()

	task, ok := me.tasks[taskID]
	if !ok {
		return fmt.Errorf("task not found: %s", taskID)
	}

	task.Status = model.MigrationStatusFailed
	task.Error = "cancelled by user"
	now := time.Now()
	task.FinishedAt = &now
	me.tasks[taskID] = task

	me.logger.Info("migration cancelled", zap.String("task_id", taskID))
	return nil
}

package replication

import (
	"context"
	"compress/gzip"
	"fmt"
	"io"
	"sync"
	"time"

	"etcd-backup-manager/internal/storage"
	"etcd-backup-manager/pkg/models"
)

type Replicator struct {
	configs map[string]*models.ReplicationConfig
	tasks   map[string]*models.ReplicationTask
	source  storage.Storage
	mu      sync.RWMutex
}

func NewReplicator(source storage.Storage) *Replicator {
	return &Replicator{
		configs: make(map[string]*models.ReplicationConfig),
		tasks:   make(map[string]*models.ReplicationTask),
		source:  source,
	}
}

func (r *Replicator) AddConfig(config *models.ReplicationConfig) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.configs[config.ID]; exists {
		return fmt.Errorf("replication config %s already exists", config.ID)
	}

	r.configs[config.ID] = config
	return nil
}

func (r *Replicator) UpdateConfig(config *models.ReplicationConfig) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.configs[config.ID]; !exists {
		return fmt.Errorf("replication config %s not found", config.ID)
	}

	config.UpdatedAt = time.Now()
	r.configs[config.ID] = config
	return nil
}

func (r *Replicator) RemoveConfig(configID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.configs, configID)
}

func (r *Replicator) GetConfig(id string) (*models.ReplicationConfig, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	config, exists := r.configs[id]
	if !exists {
		return nil, fmt.Errorf("replication config %s not found", id)
	}
	return config, nil
}

func (r *Replicator) ListConfigs(clusterID string) []*models.ReplicationConfig {
	r.mu.RLock()
	defer r.mu.RUnlock()

	configs := make([]*models.ReplicationConfig, 0)
	for _, config := range r.configs {
		if clusterID == "" || config.SourceClusterID == clusterID || config.TargetClusterID == clusterID {
			configs = append(configs, config)
		}
	}
	return configs
}

func (r *Replicator) ReplicateBackup(ctx context.Context, configID string, backup *models.Backup) (*models.ReplicationTask, error) {
	config, err := r.GetConfig(configID)
	if err != nil {
		return nil, err
	}

	if !config.Enabled {
		return nil, fmt.Errorf("replication config %s is disabled", configID)
	}

	task := models.NewReplicationTask(configID, backup.ID)
	task.Status = "running"
	r.mu.Lock()
	r.tasks[task.ID] = task
	r.mu.Unlock()

	go r.executeReplication(ctx, task, config, backup)

	return task, nil
}

func (r *Replicator) executeReplication(ctx context.Context, task *models.ReplicationTask, config *models.ReplicationConfig, backup *models.Backup) {
	defer func() {
		task.CompletedAt = time.Now()
		if !task.CompletedAt.IsZero() && !task.CreatedAt.IsZero() {
			task.Duration = int64(task.CompletedAt.Sub(task.CreatedAt).Seconds())
		}
		r.mu.Lock()
		r.tasks[task.ID] = task
		r.mu.Unlock()

		config.LastSyncAt = time.Now()
		config.LastSyncSize = task.TargetSize
		config.Status = "idle"
		r.mu.Lock()
		r.configs[config.ID] = config
		r.mu.Unlock()
	}()

	config.Status = "replicating"
	r.mu.Lock()
	r.configs[config.ID] = config
	r.mu.Unlock()

	sourceData, err := r.source.Get(ctx, backup.Path)
	if err != nil {
		task.Status = "failed"
		task.Message = fmt.Sprintf("Failed to read source backup: %v", err)
		return
	}
	task.SourceSize = int64(len(sourceData))

	targetStore, err := storage.NewStorage(config.TargetStorage)
	if err != nil {
		task.Status = "failed"
		task.Message = fmt.Sprintf("Failed to create target storage client: %v", err)
		return
	}

	replicaKey := fmt.Sprintf("replica/%s/%s", backup.ClusterID, backup.Path)

	if config.Compress {
		compressedData, err := compressData(sourceData)
		if err != nil {
			task.Status = "failed"
			task.Message = fmt.Sprintf("Failed to compress data: %v", err)
			return
		}
		sourceData = compressedData
	}

	if err := targetStore.Save(ctx, replicaKey, sourceData); err != nil {
		task.Status = "failed"
		task.Message = fmt.Sprintf("Failed to save to target storage: %v", err)
		return
	}

	targetSize, err := targetStore.GetSize(ctx, replicaKey)
	if err != nil {
		targetSize = int64(len(sourceData))
	}
	task.TargetSize = targetSize
	task.Status = "completed"
	task.Message = fmt.Sprintf("Replicated %d bytes to %s", task.SourceSize, config.TargetStorage.Type)

	backup.Replicated = true
	if backup.ReplicaSites == nil {
		backup.ReplicaSites = []string{}
	}
	backup.ReplicaSites = append(backup.ReplicaSites, config.TargetClusterID)

	if backup.MetaPath != "" {
		metaData, err := r.source.Get(ctx, backup.MetaPath)
		if err == nil {
			targetStore.Save(ctx, fmt.Sprintf("replica/%s/%s", backup.ClusterID, backup.MetaPath), metaData)
		}
	}
}

func (r *Replicator) ReplicateLatestBackups(ctx context.Context, configID string, backups []*models.Backup) ([]*models.ReplicationTask, error) {
	config, err := r.GetConfig(configID)
	if err != nil {
		return nil, err
	}

	var tasks []*models.ReplicationTask
	for _, backup := range backups {
		if backup.Status != "completed" {
			continue
		}
		if backup.Replicated {
			continue
		}

		task, err := r.ReplicateBackup(ctx, configID, backup)
		if err != nil {
			continue
		}
		tasks = append(tasks, task)
	}

	return tasks, nil
}

func (r *Replicator) GetTask(id string) (*models.ReplicationTask, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	task, exists := r.tasks[id]
	if !exists {
		return nil, fmt.Errorf("replication task %s not found", id)
	}
	return task, nil
}

func (r *Replicator) ListTasks(configID string) []*models.ReplicationTask {
	r.mu.RLock()
	defer r.mu.RUnlock()

	tasks := make([]*models.ReplicationTask, 0)
	for _, task := range r.tasks {
		if configID == "" || task.ConfigID == configID {
			tasks = append(tasks, task)
		}
	}
	return tasks
}

func (r *Replicator) GetReplicationLag(ctx context.Context, configID string) (int64, error) {
	config, err := r.GetConfig(configID)
	if err != nil {
		return 0, err
	}

	if config.LastSyncAt.IsZero() {
		return -1, nil
	}

	lag := time.Since(config.LastSyncAt).Seconds()
	return int64(lag), nil
}

func (r *Replicator) CheckTargetHealth(ctx context.Context, configID string) error {
	config, err := r.GetConfig(configID)
	if err != nil {
		return err
	}

	targetStore, err := storage.NewStorage(config.TargetStorage)
	if err != nil {
		return fmt.Errorf("failed to connect to target storage: %w", err)
	}

	testKey := fmt.Sprintf("health-check/%d", time.Now().Unix())
	if err := targetStore.Save(ctx, testKey, []byte("health-check")); err != nil {
		return fmt.Errorf("target storage write test failed: %w", err)
	}

	if _, err := targetStore.Get(ctx, testKey); err != nil {
		return fmt.Errorf("target storage read test failed: %w", err)
	}

	targetStore.Delete(ctx, testKey)
	return nil
}

func compressData(data []byte) ([]byte, error) {
	pr, pw := io.Pipe()

	go func() {
		defer pw.Close()
		gw := gzip.NewWriter(pw)
		gw.Write(data)
		gw.Close()
	}()

	return io.ReadAll(pr)
}

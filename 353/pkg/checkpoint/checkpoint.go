package checkpoint

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type TransferStatus string

const (
	StatusPending   TransferStatus = "pending"
	StatusRunning   TransferStatus = "running"
	StatusCompleted TransferStatus = "completed"
	StatusFailed    TransferStatus = "failed"
	StatusSkipped   TransferStatus = "skipped"
)

type ObjectCheckpoint struct {
	Key          string         `json:"key"`
	Size         int64          `json:"size"`
	Offset       int64          `json:"offset"`
	Status       TransferStatus `json:"status"`
	ETag         string         `json:"etag"`
	LastModified int64          `json:"last_modified"`
	RetryCount   int            `json:"retry_count"`
	LastError    string         `json:"last_error,omitempty"`
	StartTime    int64          `json:"start_time,omitempty"`
	EndTime      int64          `json:"end_time,omitempty"`
}

type MigrationCheckpoint struct {
	TaskID        string                      `json:"task_id"`
	TaskType      string                      `json:"task_type"`
	Source        string                      `json:"source"`
	Destination   string                      `json:"destination"`
	CreatedAt     int64                       `json:"created_at"`
	UpdatedAt     int64                       `json:"updated_at"`
	Status        string                      `json:"status"`
	TotalObjects  int                         `json:"total_objects"`
	Completed    int                         `json:"completed"`
	Failed       int                         `json:"failed"`
	TotalBytes    int64                       `json:"total_bytes"`
	TransferredBytes int64                    `json:"transferred_bytes"`
	Objects       map[string]ObjectCheckpoint `json:"objects"`
	Metadata      map[string]interface{}      `json:"metadata,omitempty"`
}

type CheckpointManager struct {
	checkpointDir string
	checkpoints   map[string]*MigrationCheckpoint
	mu            sync.RWMutex
}

func NewCheckpointManager(checkpointDir string) (*CheckpointManager, error) {
	if checkpointDir == "" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			checkpointDir = "./checkpoints"
		} else {
			checkpointDir = filepath.Join(homeDir, ".cloud-migration", "checkpoints")
		}
	}

	if err := os.MkdirAll(checkpointDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create checkpoint directory: %w", err)
	}

	cm := &CheckpointManager{
		checkpointDir: checkpointDir,
		checkpoints:   make(map[string]*MigrationCheckpoint),
	}

	if err := cm.loadExistingCheckpoints(); err != nil {
		return nil, err
	}

	return cm, nil
}

func (cm *CheckpointManager) loadExistingCheckpoints() error {
	files, err := os.ReadDir(cm.checkpointDir)
	if err != nil {
		return fmt.Errorf("failed to read checkpoint directory: %w", err)
	}

	for _, file := range files {
		if filepath.Ext(file.Name()) != ".json" {
			continue
		}

		data, err := os.ReadFile(filepath.Join(cm.checkpointDir, file.Name()))
		if err != nil {
			continue
		}

		var cp MigrationCheckpoint
		if err := json.Unmarshal(data, &cp); err != nil {
			continue
		}

		cm.checkpoints[cp.TaskID] = &cp
	}

	return nil
}

func (cm *CheckpointManager) CreateCheckpoint(taskID, taskType, source, destination string) *MigrationCheckpoint {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	now := time.Now().Unix()
	cp := &MigrationCheckpoint{
		TaskID:       taskID,
		TaskType:     taskType,
		Source:       source,
		Destination:  destination,
		CreatedAt:    now,
		UpdatedAt:    now,
		Status:       "initialized",
		Objects:      make(map[string]ObjectCheckpoint),
		Metadata:     make(map[string]interface{}),
	}

	cm.checkpoints[taskID] = cp
	_ = cm.saveCheckpoint(cp)
	return cp
}

func (cm *CheckpointManager) GetCheckpoint(taskID string) (*MigrationCheckpoint, bool) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	cp, exists := cm.checkpoints[taskID]
	return cp, exists
}

func (cm *CheckpointManager) GetCheckpointsByType(taskType string) []*MigrationCheckpoint {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	var result []*MigrationCheckpoint
	for _, cp := range cm.checkpoints {
		if cp.TaskType == taskType {
			result = append(result, cp)
		}
	}
	return result
}

func (cm *CheckpointManager) GetPendingCheckpoints() []*MigrationCheckpoint {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	var result []*MigrationCheckpoint
	for _, cp := range cm.checkpoints {
		if cp.Status != "completed" && cp.Status != "failed" {
			result = append(result, cp)
		}
	}
	return result
}

func (cm *CheckpointManager) AddObject(taskID string, obj ObjectCheckpoint) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return
	}

	cp.Objects[obj.Key] = obj
	cp.TotalObjects++
	cp.TotalBytes += obj.Size
	cp.UpdatedAt = time.Now().Unix()

	_ = cm.saveCheckpoint(cp)
}

func (cm *CheckpointManager) UpdateObjectProgress(taskID, key string, offset int64) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return
	}

	if obj, ok := cp.Objects[key]; ok {
		prevOffset := obj.Offset
		obj.Offset = offset
		obj.Status = StatusRunning
		cp.TransferredBytes += (offset - prevOffset)
		cp.Objects[key] = obj
		cp.UpdatedAt = time.Now().Unix()
		_ = cm.saveCheckpoint(cp)
	}
}

func (cm *CheckpointManager) MarkObjectComplete(taskID, key string, etag string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return
	}

	if obj, ok := cp.Objects[key]; ok {
		obj.Status = StatusCompleted
		obj.ETag = etag
		obj.EndTime = time.Now().Unix()
		cp.Objects[key] = obj
		cp.Completed++
		cp.UpdatedAt = time.Now().Unix()
		_ = cm.saveCheckpoint(cp)
	}
}

func (cm *CheckpointManager) MarkObjectFailed(taskID, key string, err error) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return
	}

	if obj, ok := cp.Objects[key]; ok {
		obj.Status = StatusFailed
		obj.RetryCount++
		obj.LastError = err.Error()
		cp.Objects[key] = obj
		cp.Failed++
		cp.UpdatedAt = time.Now().Unix()
		_ = cm.saveCheckpoint(cp)
	}
}

func (cm *CheckpointManager) UpdateTaskStatus(taskID, status string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return
	}

	cp.Status = status
	cp.UpdatedAt = time.Now().Unix()
	_ = cm.saveCheckpoint(cp)
}

func (cm *CheckpointManager) GetPendingObjects(taskID string) []ObjectCheckpoint {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return nil
	}

	var pending []ObjectCheckpoint
	for _, obj := range cp.Objects {
		if obj.Status == StatusPending || obj.Status == StatusFailed {
			pending = append(pending, obj)
		}
	}
	return pending
}

func (cm *CheckpointManager) GetFailedObjects(taskID string) []ObjectCheckpoint {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return nil
	}

	var failed []ObjectCheckpoint
	for _, obj := range cp.Objects {
		if obj.Status == StatusFailed {
			failed = append(failed, obj)
		}
	}
	return failed
}

func (cm *CheckpointManager) GetProgress(taskID string) (float64, int64, int64) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	cp, exists := cm.checkpoints[taskID]
	if !exists {
		return 0, 0, 0
	}

	var progress float64
	if cp.TotalBytes > 0 {
		progress = float64(cp.TransferredBytes) / float64(cp.TotalBytes) * 100
	}

	return progress, cp.TransferredBytes, cp.TotalBytes
}

func (cm *CheckpointManager) saveCheckpoint(cp *MigrationCheckpoint) error {
	data, err := json.MarshalIndent(cp, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal checkpoint: %w", err)
	}

	filename := filepath.Join(cm.checkpointDir, fmt.Sprintf("%s.json", cp.TaskID))
	return os.WriteFile(filename, data, 0644)
}

func (cm *CheckpointManager) DeleteCheckpoint(taskID string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	delete(cm.checkpoints, taskID)
	filename := filepath.Join(cm.checkpointDir, fmt.Sprintf("%s.json", taskID))
	return os.Remove(filename)
}

func (cm *CheckpointManager) CleanupCompletedCheckpoints(olderThan time.Duration) int {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cutoff := time.Now().Add(-olderThan).Unix()
	deleted := 0

	for taskID, cp := range cm.checkpoints {
		if cp.Status == "completed" && cp.UpdatedAt < cutoff {
			delete(cm.checkpoints, taskID)
			filename := filepath.Join(cm.checkpointDir, fmt.Sprintf("%s.json", taskID))
			_ = os.Remove(filename)
			deleted++
		}
	}

	return deleted
}

func (cm *CheckpointManager) GetCheckpointFilePath(taskID string) string {
	return filepath.Join(cm.checkpointDir, fmt.Sprintf("%s.json", taskID))
}

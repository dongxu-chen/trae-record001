package cache

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type CacheVolume struct {
	ID             string
	Path           string
	SizeBytes      int64
	CreatedAt      time.Time
	LastAccessedAt time.Time
	RefCount       int
	OwnerTasks     []string
	Lock           *sync.RWMutex
}

type SharedCacheManager struct {
	CacheRoot       string
	Volumes         map[string]*CacheVolume
	IndexFile       string
	MaxCacheSize    int64
	MaxVolumes      int
	DefaultTTL      time.Duration
	mu              sync.RWMutex
}

type CacheEntry struct {
	Key         string    `json:"key"`
	Value       string    `json:"value"`
	SizeBytes   int64     `json:"size_bytes"`
	CreatedAt   time.Time `json:"created_at"`
	AccessedAt  time.Time `json:"accessed_at"`
	AccessCount int       `json:"access_count"`
	TTL         time.Time `json:"ttl"`
}

type CacheIndex struct {
	Volumes       map[string]*CacheVolume `json:"volumes"`
	Entries       map[string]*CacheEntry  `json:"entries"`
	TotalSize     int64                   `json:"total_size"`
	LastCleanup   time.Time               `json:"last_cleanup"`
}

type CacheScope string

const (
	ScopeProject   CacheScope = "project"
	ScopeBranch    CacheScope = "branch"
	ScopeGlobal    CacheScope = "global"
	ScopePipeline  CacheScope = "pipeline"
)

type CacheConfig struct {
	Scope          CacheScope
	ProjectName    string
	BranchName     string
	PipelineID     string
	TaskID         string
	ReadOnly       bool
	SharedWithCI   bool
}

func NewSharedCacheManager(cacheRoot string) (*SharedCacheManager, error) {
	if err := os.MkdirAll(cacheRoot, 0755); err != nil {
		return nil, fmt.Errorf("failed to create cache root: %w", err)
	}

	manager := &SharedCacheManager{
		CacheRoot:    cacheRoot,
		Volumes:      make(map[string]*CacheVolume),
		IndexFile:    filepath.Join(cacheRoot, "cache-index.json"),
		MaxCacheSize: 50 * 1024 * 1024 * 1024,
		MaxVolumes:   100,
		DefaultTTL:   7 * 24 * time.Hour,
	}

	if err := manager.loadIndex(); err != nil {
		return nil, err
	}

	return manager, nil
}

func (scm *SharedCacheManager) loadIndex() error {
	scm.mu.Lock()
	defer scm.mu.Unlock()

	data, err := os.ReadFile(scm.IndexFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	var index CacheIndex
	if err := json.Unmarshal(data, &index); err != nil {
		return nil
	}

	scm.Volumes = index.Volumes
	return nil
}

func (scm *SharedCacheManager) saveIndex() error {
	scm.mu.Lock()
	defer scm.mu.Unlock()

	index := CacheIndex{
		Volumes:   scm.Volumes,
		Entries:   make(map[string]*CacheEntry),
		TotalSize: 0,
	}

	data, err := json.MarshalIndent(index, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(scm.IndexFile, data, 0644)
}

func (scm *SharedCacheManager) GetOrCreateVolume(config *CacheConfig) (*CacheVolume, error) {
	volumeID := scm.generateVolumeID(config)

	scm.mu.RLock()
	volume, exists := scm.Volumes[volumeID]
	scm.mu.RUnlock()

	if exists {
		if !config.ReadOnly {
			scm.mu.Lock()
			volume.LastAccessedAt = time.Now()
			volume.RefCount++
			if config.TaskID != "" {
				volume.OwnerTasks = append(volume.OwnerTasks, config.TaskID)
			}
			scm.mu.Unlock()
		}
		return volume, nil
	}

	if config.ReadOnly {
		return nil, fmt.Errorf("cache volume not found in read-only mode")
	}

	volumePath := filepath.Join(scm.CacheRoot, "volumes", volumeID)
	if err := os.MkdirAll(volumePath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create volume directory: %w", err)
	}

	volume = &CacheVolume{
		ID:             volumeID,
		Path:           volumePath,
		CreatedAt:      time.Now(),
		LastAccessedAt: time.Now(),
		RefCount:       1,
		OwnerTasks:     []string{config.TaskID},
		Lock:           &sync.RWMutex{},
	}

	scm.mu.Lock()
	scm.Volumes[volumeID] = volume
	scm.mu.Unlock()

	scm.saveIndex()

	return volume, nil
}

func (scm *SharedCacheManager) generateVolumeID(config *CacheConfig) string {
	hasher := sha256.New()

	switch config.Scope {
	case ScopeGlobal:
		hasher.Write([]byte("global"))
	case ScopeProject:
		hasher.Write([]byte(config.ProjectName))
	case ScopeBranch:
		hasher.Write([]byte(config.ProjectName + ":" + config.BranchName))
	case ScopePipeline:
		hasher.Write([]byte(config.ProjectName + ":" + config.PipelineID))
	}

	return hex.EncodeToString(hasher.Sum(nil))[:16]
}

func (scm *SharedCacheManager) StoreLayer(volume *CacheVolume, layerHash string, data []byte) error {
	if volume == nil {
		return fmt.Errorf("nil volume")
	}

	volume.Lock.Lock()
	defer volume.Lock.Unlock()

	layerPath := filepath.Join(volume.Path, layerHash[:2], layerHash)
	if err := os.MkdirAll(filepath.Dir(layerPath), 0755); err != nil {
		return err
	}

	if err := os.WriteFile(layerPath, data, 0644); err != nil {
		return err
	}

	volume.SizeBytes += int64(len(data))
	volume.LastAccessedAt = time.Now()

	scm.saveIndex()
	return nil
}

func (scm *SharedCacheManager) GetLayer(volume *CacheVolume, layerHash string) ([]byte, bool, error) {
	if volume == nil {
		return nil, false, fmt.Errorf("nil volume")
	}

	volume.Lock.RLock()
	defer volume.Lock.RUnlock()

	layerPath := filepath.Join(volume.Path, layerHash[:2], layerHash)
	data, err := os.ReadFile(layerPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, false, nil
		}
		return nil, false, err
	}

	volume.LastAccessedAt = time.Now()
	return data, true, nil
}

func (scm *SharedCacheManager) HasLayer(volume *CacheVolume, layerHash string) bool {
	if volume == nil {
		return false
	}

	volume.Lock.RLock()
	defer volume.Lock.RUnlock()

	layerPath := filepath.Join(volume.Path, layerHash[:2], layerHash)
	_, err := os.Stat(layerPath)
	return err == nil
}

func (scm *SharedCacheManager) StoreFile(volume *CacheVolume, srcPath string, destKey string) error {
	if volume == nil {
		return fmt.Errorf("nil volume")
	}

	volume.Lock.Lock()
	defer volume.Lock.Unlock()

	srcFile, err := os.Open(srcPath)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	destPath := filepath.Join(volume.Path, destKey)
	if err := os.MkdirAll(filepath.Dir(destPath), 0755); err != nil {
		return err
	}

	destFile, err := os.Create(destPath)
	if err != nil {
		return err
	}
	defer destFile.Close()

	size, err := io.Copy(destFile, srcFile)
	if err != nil {
		return err
	}

	volume.SizeBytes += size
	volume.LastAccessedAt = time.Now()
	scm.saveIndex()

	return nil
}

func (scm *SharedCacheManager) RestoreFile(volume *CacheVolume, srcKey string, destPath string) (bool, error) {
	if volume == nil {
		return false, fmt.Errorf("nil volume")
	}

	volume.Lock.RLock()
	defer volume.Lock.RUnlock()

	srcPath := filepath.Join(volume.Path, srcKey)
	srcFile, err := os.Open(srcPath)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, err
	}
	defer srcFile.Close()

	if err := os.MkdirAll(filepath.Dir(destPath), 0755); err != nil {
		return false, err
	}

	destFile, err := os.Create(destPath)
	if err != nil {
		return false, err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, srcFile)
	if err != nil {
		return false, err
	}

	volume.LastAccessedAt = time.Now()
	return true, nil
}

func (scm *SharedCacheManager) Cleanup() (int64, int, error) {
	scm.mu.Lock()
	defer scm.mu.Unlock()

	var freedSize int64
	var removedCount int

	now := time.Now()
	for id, volume := range scm.Volumes {
		if now.Sub(volume.LastAccessedAt) > scm.DefaultTTL {
			if err := os.RemoveAll(volume.Path); err == nil {
				freedSize += volume.SizeBytes
				removedCount++
				delete(scm.Volumes, id)
			}
		}
	}

	var totalSize int64
	for _, volume := range scm.Volumes {
		totalSize += volume.SizeBytes
	}

	if totalSize > scm.MaxCacheSize {
		type volumeInfo struct {
			id         string
			lastAccess time.Time
			size       int64
		}
		var volumes []volumeInfo
		for id, v := range scm.Volumes {
			volumes = append(volumes, volumeInfo{id, v.LastAccessedAt, v.SizeBytes})
		}

		for i := 0; i < len(volumes); i++ {
			for j := i + 1; j < len(volumes); j++ {
				if volumes[i].lastAccess.After
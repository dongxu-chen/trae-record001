package cache

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	"github.com/jenkins-cache-sharing/internal/checksum"
	"github.com/jenkins-cache-sharing/internal/model"
	"github.com/jenkins-cache-sharing/internal/storage"
	"go.uber.org/zap"
)

type MetaStore struct {
	mu       sync.RWMutex
	entries  map[string]*model.CacheEntry
	versions map[string]*model.CacheVersion
	storeDir string
	logger   *zap.Logger
}

func NewMetaStore(storeDir string, logger *zap.Logger) (*MetaStore, error) {
	if err := os.MkdirAll(storeDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create meta store dir: %w", err)
	}

	ms := &MetaStore{
		entries:  make(map[string]*model.CacheEntry),
		versions: make(map[string]*model.CacheVersion),
		storeDir: storeDir,
		logger:   logger,
	}

	if err := ms.load(); err != nil {
		logger.Warn("failed to load existing metadata, starting fresh", zap.Error(err))
	}

	return ms, nil
}

func (ms *MetaStore) load() error {
	entriesPath := filepath.Join(ms.storeDir, "entries.json")
	if data, err := os.ReadFile(entriesPath); err == nil {
		if err := json.Unmarshal(data, &ms.entries); err != nil {
			return fmt.Errorf("failed to unmarshal entries: %w", err)
		}
	}

	versionsPath := filepath.Join(ms.storeDir, "versions.json")
	if data, err := os.ReadFile(versionsPath); err == nil {
		if err := json.Unmarshal(data, &ms.versions); err != nil {
			return fmt.Errorf("failed to unmarshal versions: %w", err)
		}
	}

	ms.logger.Info("loaded metadata",
		zap.Int("entries", len(ms.entries)),
		zap.Int("versions", len(ms.versions)),
	)
	return nil
}

func (ms *MetaStore) save() error {
	entriesData, err := json.MarshalIndent(ms.entries, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal entries: %w", err)
	}
	if err := os.WriteFile(filepath.Join(ms.storeDir, "entries.json"), entriesData, 0644); err != nil {
		return fmt.Errorf("failed to write entries: %w", err)
	}

	versionsData, err := json.MarshalIndent(ms.versions, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal versions: %w", err)
	}
	if err := os.WriteFile(filepath.Join(ms.storeDir, "versions.json"), versionsData, 0644); err != nil {
		return fmt.Errorf("failed to write versions: %w", err)
	}

	return nil
}

type VersionManager struct {
	meta   *MetaStore
	storage *storage.ObjectStorage
	logger  *zap.Logger
}

func NewVersionManager(meta *MetaStore, objStorage *storage.ObjectStorage, logger *zap.Logger) *VersionManager {
	return &VersionManager{
		meta:    meta,
		storage: objStorage,
		logger:  logger,
	}
}

func (vm *VersionManager) CreateEntry(ctx context.Context, entry *model.CacheEntry) (*model.CacheEntry, error) {
	vm.meta.mu.Lock()
	defer vm.meta.mu.Unlock()

	if entry.ID == "" {
		entry.ID = generateID()
	}
	now := time.Now()
	entry.CreatedAt = now
	entry.UpdatedAt = now
	entry.Status = model.CacheStatusActive

	if entry.ObjectKey == "" {
		entry.ObjectKey = storage.BuildObjectKey(entry.Type, entry.JobName, entry.BuildNumber, entry.Version)
	}

	vm.meta.entries[entry.ID] = entry

	vm.ensureVersion(entry)

	if err := vm.meta.save(); err != nil {
		vm.logger.Error("failed to save metadata", zap.Error(err))
	}

	vm.logger.Info("created cache entry",
		zap.String("id", entry.ID),
		zap.String("type", string(entry.Type)),
		zap.String("version", entry.Version),
		zap.String("dependency_hash", entry.DependencyHash),
	)

	return entry, nil
}

func (vm *VersionManager) CreateEntryWithDependencies(
	ctx context.Context,
	entry *model.CacheEntry,
	fileContents map[string]string,
) (*model.CacheEntry, string, bool, error) {
	depHash, err := checksum.ComputeHashFromContents(entry.Type, fileContents)
	if err != nil {
		return nil, "", false, fmt.Errorf("failed to compute dependency hash: %w", err)
	}

	entry.DependencyHash = depHash.Combined
	entry.DependencyFiles = make([]model.DependencyFileHash, 0, len(depHash.Files))
	for _, f := range depHash.Files {
		entry.DependencyFiles = append(entry.DependencyFiles, model.DependencyFileHash{
			Path: f.Path,
			Hash: f.Hash,
		})
	}

	previousHash := vm.GetLatestDependencyHash(ctx, entry.Type, entry.JobName)
	changed := checksum.HasDependencyChanged(depHash.Combined, previousHash)

	created, err := vm.CreateEntry(ctx, entry)
	if err != nil {
		return nil, depHash.Combined, changed, err
	}

	return created, depHash.Combined, changed, nil
}

func (vm *VersionManager) GetLatestDependencyHash(ctx context.Context, cacheType model.CacheType, jobName string) string {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	var latestEntry *model.CacheEntry
	for _, entry := range vm.meta.entries {
		if entry.Type == cacheType && entry.JobName == jobName && entry.DependencyHash != "" {
			if latestEntry == nil || entry.CreatedAt.After(latestEntry.CreatedAt) {
				latestEntry = entry
			}
		}
	}

	if latestEntry != nil {
		return latestEntry.DependencyHash
	}
	return ""
}

func (vm *VersionManager) CheckDependencyChange(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	fileContents map[string]string,
) (*model.DependencyChangeEvent, error) {
	depHash, err := checksum.ComputeHashFromContents(cacheType, fileContents)
	if err != nil {
		return nil, fmt.Errorf("failed to compute dependency hash: %w", err)
	}

	previousHash := vm.GetLatestDependencyHash(ctx, cacheType, jobName)

	if !checksum.HasDependencyChanged(depHash.Combined, previousHash) {
		return nil, nil
	}

	changedFiles := vm.findChangedFiles(ctx, cacheType, jobName, depHash)

	event := &model.DependencyChangeEvent{
		ID:           generateID(),
		CacheType:    cacheType,
		JobName:      jobName,
		PreviousHash: previousHash,
		CurrentHash:  depHash.Combined,
		ChangedFiles: changedFiles,
		AutoWarmed:   false,
		CreatedAt:    time.Now(),
	}

	return event, nil
}

func (vm *VersionManager) findChangedFiles(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	newHash *checksum.DependencyHash,
) []string {
	latestEntry := vm.getLatestEntryForJob(ctx, cacheType, jobName)
	if latestEntry == nil {
		var files []string
		for _, f := range newHash.Files {
			files = append(files, f.Path)
		}
		return files
	}

	previousMap := make(map[string]string)
	for _, f := range latestEntry.DependencyFiles {
		previousMap[f.Path] = f.Hash
	}

	var changed []string
	for _, f := range newHash.Files {
		prevHash, exists := previousMap[f.Path]
		if !exists || prevHash != f.Hash {
			changed = append(changed, f.Path)
		}
	}

	return changed
}

func (vm *VersionManager) getLatestEntryForJob(ctx context.Context, cacheType model.CacheType, jobName string) *model.CacheEntry {
	var latest *model.CacheEntry
	for _, entry := range vm.meta.entries {
		if entry.Type == cacheType && entry.JobName == jobName {
			if latest == nil || entry.CreatedAt.After(latest.CreatedAt) {
				latest = entry
			}
		}
	}
	return latest
}

func (vm *VersionManager) ComputeHashForDir(cacheType model.CacheType, projectDir string) (*checksum.DependencyHash, error) {
	return checksum.ComputeDependencyHash(cacheType, projectDir)
}

func (vm *VersionManager) ComputeHashForContents(cacheType model.CacheType, fileContents map[string]string) (*checksum.DependencyHash, error) {
	return checksum.ComputeHashFromContents(cacheType, fileContents)
}

func (vm *VersionManager) GetEntriesOrderedByAccess(ctx context.Context, cacheType model.CacheType, jobName string) []*model.CacheEntry {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	var entries []*model.CacheEntry
	for _, entry := range vm.meta.entries {
		if cacheType != "" && entry.Type != cacheType {
			continue
		}
		if jobName != "" && entry.JobName != jobName {
			continue
		}
		if entry.Status != model.CacheStatusActive {
			continue
		}
		entries = append(entries, entry)
	}

	sort.Slice(entries, func(i, j int) bool {
		iScore := vm.getLRUScore(entries[i])
		jScore := vm.getLRUScore(entries[j])
		return iScore < jScore
	})

	return entries
}

func (vm *VersionManager) getLRUScore(entry *model.CacheEntry) float64 {
	now := time.Now()
	var lastAccess time.Time
	if entry.LastAccess != nil {
		lastAccess = *entry.LastAccess
	} else {
		lastAccess = entry.CreatedAt
	}

	hoursSince := now.Sub(lastAccess).Hours()
	return hoursSince - float64(entry.AccessCount)*10
}

func (vm *VersionManager) GetTotalSize(ctx context.Context, cacheType model.CacheType) int64 {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	var total int64
	for _, entry := range vm.meta.entries {
		if entry.Status != model.CacheStatusActive {
			continue
		}
		if cacheType == "" || entry.Type == cacheType {
			total += entry.Size
		}
	}
	return total
}

func (vm *VersionManager) RecordDependencyWarmup(eventID string, warmupTaskID string) error {
	vm.meta.mu.Lock()
	defer vm.meta.mu.Unlock()

	_ = eventID
	_ = warmupTaskID

	if err := vm.meta.save(); err != nil {
		vm.logger.Error("failed to save metadata", zap.Error(err))
	}
	return nil
}

func (vm *VersionManager) ensureVersion(entry *model.CacheEntry) {
	versionKey := fmt.Sprintf("%s:%s", entry.Type, entry.Version)

	var existingVersion *model.CacheVersion
	for _, v := range vm.meta.versions {
		if v.CacheType == entry.Type && v.Version == entry.Version {
			existingVersion = v
			break
		}
	}

	if existingVersion == nil {
		newVersion := &model.CacheVersion{
			ID:          generateID(),
			CacheType:   entry.Type,
			Version:     entry.Version,
			Entries:     []string{entry.ID},
			IsLatest:    true,
			Description: fmt.Sprintf("Auto-created version for %s", entry.Version),
			CreatedAt:   time.Now(),
		}

		for _, v := range vm.meta.versions {
			if v.CacheType == entry.Type && v.IsLatest {
				v.IsLatest = false
			}
		}

		vm.meta.versions[versionKey] = newVersion
	} else {
		found := false
		for _, eid := range existingVersion.Entries {
			if eid == entry.ID {
				found = true
				break
			}
		}
		if !found {
			existingVersion.Entries = append(existingVersion.Entries, entry.ID)
		}
	}
}

func (vm *VersionManager) GetEntry(ctx context.Context, id string) (*model.CacheEntry, error) {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	entry, ok := vm.meta.entries[id]
	if !ok {
		return nil, fmt.Errorf("cache entry not found: %s", id)
	}
	return entry, nil
}

func (vm *VersionManager) ListEntries(ctx context.Context, cacheType model.CacheType, jobName string, page, pageSize int) (*model.PaginatedResult, error) {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	var filtered []*model.CacheEntry
	for _, entry := range vm.meta.entries {
		if cacheType != "" && entry.Type != cacheType {
			continue
		}
		if jobName != "" && entry.JobName != jobName {
			continue
		}
		filtered = append(filtered, entry)
	}

	total := int64(len(filtered))
	totalPages := (int(total) + pageSize - 1) / pageSize
	if totalPages == 0 {
		totalPages = 1
	}

	start := (page - 1) * pageSize
	if start >= int(total) {
		start = int(total)
	}
	end := start + pageSize
	if end > int(total) {
		end = int(total)
	}

	var items []*model.CacheEntry
	if start < end {
		items = filtered[start:end]
	}

	return &model.PaginatedResult{
		Items:      items,
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	}, nil
}

func (vm *VersionManager) UpdateEntry(ctx context.Context, id string, updates func(*model.CacheEntry)) (*model.CacheEntry, error) {
	vm.meta.mu.Lock()
	defer vm.meta.mu.Unlock()

	entry, ok := vm.meta.entries[id]
	if !ok {
		return nil, fmt.Errorf("cache entry not found: %s", id)
	}

	updates(entry)
	entry.UpdatedAt = time.Now()

	if err := vm.meta.save(); err != nil {
		vm.logger.Error("failed to save metadata", zap.Error(err))
	}

	return entry, nil
}

func (vm *VersionManager) DeleteEntry(ctx context.Context, id string) error {
	vm.meta.mu.Lock()
	defer vm.meta.mu.Unlock()

	entry, ok := vm.meta.entries[id]
	if !ok {
		return fmt.Errorf("cache entry not found: %s", id)
	}

	if err := vm.storage.Delete(ctx, entry.ObjectKey); err != nil {
		vm.logger.Error("failed to delete object from storage", zap.Error(err))
	}

	delete(vm.meta.entries, id)

	for _, v := range vm.meta.versions {
		for i, eid := range v.Entries {
			if eid == id {
				v.Entries = append(v.Entries[:i], v.Entries[i+1:]...)
				break
			}
		}
	}

	if err := vm.meta.save(); err != nil {
		vm.logger.Error("failed to save metadata", zap.Error(err))
	}

	vm.logger.Info("deleted cache entry", zap.String("id", id))
	return nil
}

func (vm *VersionManager) GetVersions(ctx context.Context, cacheType model.CacheType) ([]*model.CacheVersion, error) {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	var versions []*model.CacheVersion
	for _, v := range vm.meta.versions {
		if cacheType != "" && v.CacheType != cacheType {
			continue
		}
		versions = append(versions, v)
	}
	return versions, nil
}

func (vm *VersionManager) PromoteVersion(ctx context.Context, cacheType model.CacheType, version string) error {
	vm.meta.mu.Lock()
	defer vm.meta.mu.Unlock()

	for _, v := range vm.meta.versions {
		if v.CacheType == cacheType {
			if v.Version == version {
				v.IsLatest = true
			} else {
				v.IsLatest = false
			}
		}
	}

	if err := vm.meta.save(); err != nil {
		vm.logger.Error("failed to save metadata", zap.Error(err))
	}

	vm.logger.Info("promoted version", zap.String("type", string(cacheType)), zap.String("version", version))
	return nil
}

func (vm *VersionManager) GetStats(ctx context.Context) (*model.CacheStats, error) {
	vm.meta.mu.RLock()
	defer vm.meta.mu.RUnlock()

	stats := &model.CacheStats{
		ByType:     make(map[model.CacheType]int64),
		ByTypeSize: make(map[model.CacheType]int64),
	}

	for _, entry := range vm.meta.entries {
		stats.TotalCaches++
		stats.TotalSize += entry.Size

		stats.ByType[entry.Type]++
		stats.ByTypeSize[entry.Type] += entry.Size

		switch entry.Status {
		case model.CacheStatusActive:
			stats.ActiveCount++
		case model.CacheStatusArchived:
			stats.ArchivedCount++
		case model.CacheStatusExpired:
			stats.ExpiredCount++
		}
	}

	return stats, nil
}

func (vm *VersionManager) RecordAccess(ctx context.Context, id string) error {
	return vm.UpdateEntry(ctx, id, func(e *model.CacheEntry) {
		e.AccessCount++
		now := time.Now()
		e.LastAccess = &now
	})
}

func generateID() string {
	b := make([]byte, 4)
	rand.Read(b)
	return hex.EncodeToString(b)
}

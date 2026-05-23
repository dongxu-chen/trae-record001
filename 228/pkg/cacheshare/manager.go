package cacheshare

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"sync"
	"time"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/filters"
	"github.com/docker/docker/client"
)

type CacheVolume struct {
	Name         string    `json:"name"`
	ID           string    `json:"id"`
	CreatedAt    time.Time `json:"created_at"`
	LastUsedAt   time.Time `json:"last_used_at"`
	SizeBytes    int64     `json:"size_bytes"`
	RefCount     int       `json:"ref_count"`
	ProjectID    string    `json:"project_id"`
	CacheType    string    `json:"cache_type"`
	Labels       map[string]string `json:"labels"`
}

type CacheShareConfig struct {
	CacheDir         string
	MaxCacheSizeGB   float64
	RetentionDays    int
	SharedVolumeName string
}

type CacheShareManager struct {
	cli            *client.Client
	config         *CacheShareConfig
	volumes        map[string]*CacheVolume
	activeLocks    map[string]*sync.Mutex
	mu             sync.RWMutex
	metadataFile   string
}

type CIJob struct {
	ID        string
	ProjectID string
	Branch    string
	CommitSHA string
}

type CacheUsageReport struct {
	TotalSizeBytes     int64              `json:"total_size_bytes"`
	UsedSizeBytes      int64              `json:"used_size_bytes"`
	AvailableSizeBytes int64              `json:"available_size_bytes"`
	VolumeCount        int                `json:"volume_count"`
	Volumes            []*CacheVolume     `json:"volumes"`
	SpaceSavedBytes    int64              `json:"space_saved_bytes"`
	DeduplicationRate  float64            `json:"deduplication_rate"`
}

func DefaultConfig() *CacheShareConfig {
	cacheDir := "/var/cache/docker-build"
	if runtime.GOOS == "windows" {
		cacheDir = "C:\\ProgramData\\docker-build-cache"
	}

	return &CacheShareConfig{
		CacheDir:         cacheDir,
		MaxCacheSizeGB:   50,
		RetentionDays:    30,
		SharedVolumeName: "shared-build-cache",
	}
}

func NewCacheShareManager(cli *client.Client, config *CacheShareConfig) (*CacheShareManager, error) {
	if config == nil {
		config = DefaultConfig()
	}

	manager := &CacheShareManager{
		cli:          cli,
		config:       config,
		volumes:      make(map[string]*CacheVolume),
		activeLocks:  make(map[string]*sync.Mutex),
		metadataFile: filepath.Join(config.CacheDir, "cache-metadata.json"),
	}

	if err := manager.ensureCacheDir(); err != nil {
		return nil, err
	}

	if err := manager.loadMetadata(); err != nil {
		return nil, err
	}

	return manager, nil
}

func (csm *CacheShareManager) ensureCacheDir() error {
	if err := os.MkdirAll(csm.config.CacheDir, 0755); err != nil {
		return fmt.Errorf("failed to create cache directory: %w", err)
	}
	return nil
}

func (csm *CacheShareManager) loadMetadata() error {
	csm.mu.Lock()
	defer csm.mu.Unlock()

	data, err := os.ReadFile(csm.metadataFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	var metadata struct {
		Volumes map[string]*CacheVolume `json:"volumes"`
	}

	if err := json.Unmarshal(data, &metadata); err != nil {
		return err
	}

	csm.volumes = metadata.Volumes
	for _, v := range csm.volumes {
		csm.activeLocks[v.Name] = &sync.Mutex{}
	}

	return nil
}

func (csm *CacheShareManager) saveMetadata() error {
	csm.mu.RLock()
	defer csm.mu.RUnlock()

	metadata := struct {
		Volumes     map[string]*CacheVolume `json:"volumes"`
		LastUpdated time.Time               `json:"last_updated"`
	}{
		Volumes:     csm.volumes,
		LastUpdated: time.Now(),
	}

	data, err := json.MarshalIndent(metadata, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(csm.metadataFile, data, 0644)
}

func (csm *CacheShareManager) GetSharedVolume(ctx context.Context, job *CIJob) (*CacheVolume, error) {
	volumeName := csm.generateVolumeName(job)

	csm.mu.Lock()
	if _, exists := csm.activeLocks[volumeName]; !exists {
		csm.activeLocks[volumeName] = &sync.Mutex{}
	}
	lock := csm.activeLocks[volumeName]
	csm.mu.Unlock()

	lock.Lock()
	defer lock.Unlock()

	volume, err := csm.findOrCreateVolume(ctx, volumeName, job)
	if err != nil {
		return nil, err
	}

	csm.mu.Lock()
	volume.LastUsedAt = time.Now()
	volume.RefCount++
	csm.volumes[volumeName] = volume
	csm.mu.Unlock()

	csm.saveMetadata()

	return volume, nil
}

func (csm *CacheShareManager) generateVolumeName(job *CIJob) string {
	if job.Branch == "main" || job.Branch == "master" {
		return fmt.Sprintf("%s-%s", csm.config.SharedVolumeName, job.ProjectID)
	}
	return fmt.Sprintf("%s-%s-%s", csm.config.SharedVolumeName, job.ProjectID, job.Branch)
}

func (csm *CacheShareManager) findOrCreateVolume(ctx context.Context, name string, job *CIJob) (*CacheVolume, error) {
	volumeFilters := filters.NewArgs()
	volumeFilters.Add("name", name)

	volumes, err := csm.cli.VolumeList(ctx, volumeFilters)
	if err != nil {
		return nil, err
	}

	if len(volumes.Volumes) > 0 {
		vol := volumes.Volumes[0]
		size := csm.getVolumeSize(vol.Name)
		cachedVol := &CacheVolume{
			Name:      vol.Name,
			ID:        vol.Name,
			CreatedAt: time.Now(),
			SizeBytes: size,
			ProjectID: job.ProjectID,
			Labels:    vol.Labels,
		}

		if existing, exists := csm.volumes[name]; exists {
			cachedVol.CreatedAt = existing.CreatedAt
			cachedVol.RefCount = existing.RefCount
		}

		return cachedVol, nil
	}

	return csm.createVolume(ctx, name, job)
}

func (csm *CacheShareManager) createVolume(ctx context.Context, name string, job *CIJob) (*CacheVolume, error) {
	labels := map[string]string{
		"managed_by":    "docker-build-accelerator",
		"project_id":    job.ProjectID,
		"branch":        job.Branch,
		"cache_type":    "build-cache",
		"created_at":    time.Now().Format(time.RFC3339),
	}

	volume, err := csm.cli.VolumeCreate(ctx, types.VolumeCreateRequest{
		Name:   name,
		Labels: labels,
	})
	if err != nil {
		return nil, err
	}

	cachedVol := &CacheVolume{
		Name:      volume.Name,
		ID:        volume.Name,
		CreatedAt: time.Now(),
		SizeBytes: 0,
		RefCount:  0,
		ProjectID: job.ProjectID,
		Labels:    labels,
	}

	csm.mu.Lock()
	csm.volumes[name] = cachedVol
	csm.mu.Unlock()

	return cachedVol, nil
}

func (csm *CacheShareManager) getVolumeSize(name string) int64 {
	volumePath := filepath.Join(csm.config.CacheDir, name)
	info, err := os.Stat(volumePath)
	if err != nil {
		return 0
	}
	if info.IsDir() {
		return csm.getDirSize(volumePath)
	}
	return info.Size()
}

func (csm *CacheShareManager) getDirSize(path string) int64 {
	var size int64
	filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() {
			size += info.Size()
		}
		return nil
	})
	return size
}

func (csm *CacheShareManager) ReleaseVolume(volumeName string) {
	csm.mu.Lock()
	defer csm.mu.Unlock()

	if vol, exists := csm.volumes[volumeName]; exists {
		vol.LastUsedAt = time.Now()
		if vol.RefCount > 0 {
			vol.RefCount--
		}
	}

	csm.saveMetadata()
}

func (csm *CacheShareManager) GetUsageReport(ctx context.Context) (*CacheUsageReport, error) {
	report := &CacheUsageReport{
		TotalSizeBytes:     int64(csm.config.MaxCacheSizeGB * 1024 * 1024 * 1024),
		Volumes:            make([]*CacheVolume, 0, len(csm.volumes)),
	}

	volumeFilters := filters.NewArgs()
	volumeFilters.Add("label", "managed_by=docker-build-accelerator")

	volumes, err := csm.cli.VolumeList(ctx, volumeFilters)
	if err != nil {
		return nil, err
	}

	var totalUsed int64
	var potentialDuplicates int64

	for _, vol := range volumes.Volumes {
		size := csm.getVolumeSize(vol.Name)
		cachedVol := &CacheVolume{
			Name:      vol.Name,
			ID:        vol.Name,
			SizeBytes: size,
			Labels:    vol.Labels,
		}

		if existing, exists := csm.volumes[vol.Name]; exists {
			cachedVol.CreatedAt = existing.CreatedAt
			cachedVol.LastUsedAt = existing.LastUsedAt
			cachedVol.RefCount = existing.RefCount
			cachedVol.ProjectID = existing.ProjectID
		}

		report.Volumes = append(report.Volumes, cachedVol)
		report.UsedSizeBytes += size
		totalUsed += size

		if cachedVol.RefCount > 1 {
			potentialDuplicates += size * int64(cachedVol.RefCount-1)
		}
	}

	report.AvailableSizeBytes = report.TotalSizeBytes - report.UsedSizeBytes
	report.VolumeCount = len(report.Volumes)
	report.SpaceSavedBytes = potentialDuplicates

	if report.UsedSizeBytes+potentialDuplicates > 0 {
		report.DeduplicationRate = float64(potentialDuplicates) / float64(report.UsedSizeBytes+potentialDuplicates) * 100
	}

	sort.Slice(report.Volumes, func(i, j int) bool {
		return report.Volumes[i].LastUsedAt.After(report.Volumes[j].LastUsedAt)
	})

	return report, nil
}

func (csm *CacheShareManager) Cleanup(ctx context.Context, dryRun bool) (int64, error) {
	report, err := csm.GetUsageReport(ctx)
	if err != nil {
		return 0, err
	}

	var freedSpace int64
	cutoffTime := time.Now().AddDate(0, 0, -csm.config.RetentionDays)

	for _, vol := range report.Volumes {
		if vol.LastUsedAt.Before(cutoffTime) && vol.RefCount == 0 {
			if !dryRun {
				if err := csm.cli.VolumeRemove(ctx, vol.Name, true); err != nil {
					continue
				}
				csm.mu.Lock()
				delete(csm.volumes, vol.Name)
				delete(csm.activeLocks, vol.Name)
				csm.mu.Unlock()
			}
			freedSpace += vol.SizeBytes
		}
	}

	maxSizeBytes := int64(csm.config.MaxCacheSizeGB * 1024 * 1024 * 1024)
	if report.UsedSizeBytes > maxSizeBytes {
		sort.Slice(report.Volumes, func(i, j int) bool {
			return report.Volumes[i].LastUsedAt.Before(report.Volumes[j].LastUsedAt)
		})

		for _, vol := range report.Volumes {
			if report.UsedSizeBytes-freedSpace <= maxSizeBytes {
				break
			}
			if vol.RefCount == 0 {
				if !dryRun {
					if err := csm.cli.VolumeRemove(ctx, vol.Name, true); err != nil {
						continue
					}
					csm.mu.Lock()
					delete(csm.volumes, vol.Name)
					delete(csm.activeLocks, vol.Name)
					csm.mu.Unlock()
				}
				freedSpace += vol.SizeBytes
			}
		}
	}

	csm.saveMetadata()

	return freedSpace, nil
}

func (csm *CacheShareManager) PromoteBranchCache(ctx context.Context, job *CIJob, sourceBranch, targetBranch string) error {
	sourceName := fmt.Sprintf("%s-%s-%s", csm.config.SharedVolumeName, job.ProjectID, sourceBranch)
	targetName := fmt.Sprintf("%s-%s", csm.config.SharedVolumeName, job.ProjectID)

	csm.mu.Lock()
	sourceLock, sourceExists := csm.activeLocks[sourceName]
	targetLock, targetExists := csm.activeLocks[targetName]
	if !sourceExists {
		sourceLock = &sync.Mutex{}
		csm.activeLocks[sourceName] = sourceLock
	}
	if !targetExists {
		targetLock = &sync.Mutex{}
		csm.activeLocks[targetName] = targetLock
	}
	csm.mu.Unlock()

	sourceLock.Lock()
	defer sourceLock.Unlock()
	targetLock.Lock()
	defer targetLock.Unlock()

	sourceVol, err := csm.findOrCreateVolume(ctx, sourceName, job)
	if err != nil {
		return err
	}

	_, err = csm.findOrCreateVolume(ctx, targetName, job)
	if err != nil {
		return err
	}

	csm.mu.Lock()
	if targetVol, exists := csm.volumes[targetName]; exists {
		targetVol.CreatedAt = sourceVol.CreatedAt
		targetVol.LastUsedAt = time.Now()
	}
	csm.mu.Unlock()

	csm.saveMetadata()

	return nil
}

func (report *CacheUsageReport) Print() {
	fmt.Println("\n=== 共享缓存使用报告 ===")
	fmt.Printf("总容量: %s\n", formatBytes(uint64(report.TotalSizeBytes)))
	fmt.Printf("已使用: %s\n", formatBytes(uint64(report.UsedSizeBytes)))
	fmt.Printf("可用: %s\n", formatBytes(uint64(report.AvailableSizeBytes)))
	fmt.Printf("使用率: %.1f%%\n", float64(report.UsedSizeBytes)/float64(report.TotalSizeBytes)*100)
	fmt.Printf("节省空间: %s\n", formatBytes(uint64(report.SpaceSavedBytes)))
	fmt.Printf("去重率: %.1f%%\n", report.DeduplicationRate)
	fmt.Printf("缓存卷数量: %d\n\n", report.VolumeCount)

	fmt.Println("--- 缓存卷详情 ---")
	for i, vol := range report.Volumes {
		if i >= 10 {
			fmt.Printf("  ... 还有 %d 个缓存卷\n", len(report.Volumes)-10)
			break
		}
		lastUsed := "never"
		if !vol.LastUsedAt.IsZero() {
			lastUsed = time.Since(vol.LastUsedAt).Round(time.Minute).String() + " ago"
		}
		fmt.Printf("  %s | %s | Refs: %d | Last: %s | Project: %s\n",
			vol.Name,
			formatBytes(uint64(vol.SizeBytes)),
			vol.RefCount,
			lastUsed,
			vol.ProjectID)
	}
}

func formatBytes(b uint64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := uint64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(b)/float64(div), "KMGTPE"[exp])
}

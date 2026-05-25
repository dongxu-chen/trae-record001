package cache

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"path/filepath"
	"sort"
	"strings"

	"github.com/cicache/pkg/storage"
)

type CacheSharingManager struct {
	storage      storage.Storage
	registryKey  string
	cacheDir     string
}

type SharedCacheEntry struct {
	CacheKey    string   `json:"cache_key"`
	ProjectType string   `json:"project_type"`
	Tags        []string `json:"tags"`
	DepSignature string  `json:"dep_signature"`
	Deps        []string `json:"deps"`
	CreatedAt   int64    `json:"created_at"`
	Size        int64    `json:"size"`
	HitCount    int64    `json:"hit_count"`
}

type CacheRegistry struct {
	Entries map[string]*SharedCacheEntry `json:"entries"`
}

func NewCacheSharingManager(store storage.Storage, cacheDir string) *CacheSharingManager {
	return &CacheSharingManager{
		storage:     store,
		registryKey: "shared_cache_registry.json",
		cacheDir:    cacheDir,
	}
}

func (sm *CacheSharingManager) GenerateDepSignature(deps []string) string {
	sort.Strings(deps)
	hash := sha256.New()
	for _, dep := range deps {
		hash.Write([]byte(dep))
	}
	return hex.EncodeToString(hash.Sum(nil))[:16]
}

func (sm *CacheSharingManager) GenerateTags(projectType string, deps []string) []string {
	tags := make([]string, 0)
	tags = append(tags, "type:"+projectType)

	for _, dep := range deps {
		base := filepath.Base(dep)
		if strings.HasPrefix(base, "package") {
			tags = append(tags, "pkg:nodejs")
		} else if strings.HasPrefix(base, "go.") {
			tags = append(tags, "pkg:golang")
		} else if strings.HasPrefix(base, "pom.") || strings.HasPrefix(base, "build.gradle") {
			tags = append(tags, "pkg:java")
		} else if strings.Contains(base, "requirements") || strings.HasPrefix(base, "setup.") {
			tags = append(tags, "pkg:python")
		}
	}

	return deduplicate(tags)
}

func deduplicate(items []string) []string {
	seen := make(map[string]bool)
	result := make([]string, 0)
	for _, item := range items {
		if !seen[item] {
			seen[item] = true
			result = append(result, item)
		}
	}
	return result
}

func (sm *CacheSharingManager) loadRegistry(ctx context.Context) (*CacheRegistry, error) {
	exists, err := sm.storage.Exists(ctx, sm.registryKey)
	if err != nil {
		return nil, err
	}

	if !exists {
		return &CacheRegistry{
			Entries: make(map[string]*SharedCacheEntry),
		}, nil
	}

	reader, err := sm.storage.Download(ctx, sm.registryKey)
	if err != nil {
		return nil, err
	}
	defer reader.Close()

	var registry CacheRegistry
	if err := json.NewDecoder(reader).Decode(&registry); err != nil {
		return &CacheRegistry{
			Entries: make(map[string]*SharedCacheEntry),
		}, nil
	}

	if registry.Entries == nil {
		registry.Entries = make(map[string]*SharedCacheEntry)
	}

	return &registry, nil
}

func (sm *CacheSharingManager) saveRegistry(ctx context.Context, registry *CacheRegistry) error {
	data, err := json.MarshalIndent(registry, "", "  ")
	if err != nil {
		return err
	}

	return sm.storage.Upload(ctx, sm.registryKey, bytes.NewReader(data), int64(len(data)))
}

func (sm *CacheSharingManager) RegisterCache(ctx context.Context, cacheKey string, projectType string, deps []string, size int64) error {
	registry, err := sm.loadRegistry(ctx)
	if err != nil {
		return err
	}

	signature := sm.GenerateDepSignature(deps)
	tags := sm.GenerateTags(projectType, deps)

	entry := &SharedCacheEntry{
		CacheKey:     cacheKey,
		ProjectType:  projectType,
		Tags:         tags,
		DepSignature: signature,
		Deps:         deps,
		CreatedAt:    0,
		Size:         size,
		HitCount:     0,
	}

	if existing, ok := registry.Entries[cacheKey]; ok {
		entry.HitCount = existing.HitCount + 1
	}

	registry.Entries[cacheKey] = entry
	return sm.saveRegistry(ctx, registry)
}

func (sm *CacheSharingManager) FindSimilarCaches(ctx context.Context, projectType string, deps []string) ([]*SharedCacheEntry, error) {
	registry, err := sm.loadRegistry(ctx)
	if err != nil {
		return nil, err
	}

	targetSignature := sm.GenerateDepSignature(deps)
	targetTags := sm.GenerateTags(projectType, deps)

	candidates := make([]*SharedCacheEntry, 0)
	for _, entry := range registry.Entries {
		score := sm.calculateSimilarity(entry, targetSignature, targetTags, deps)
		if score > 0.5 {
			candidates = append(candidates, entry)
		}
	}

	sort.Slice(candidates, func(i, j int) bool {
		scoreI := sm.calculateSimilarity(candidates[i], targetSignature, targetTags, deps)
		scoreJ := sm.calculateSimilarity(candidates[j], targetSignature, targetTags, deps)
		return scoreI > scoreJ
	})

	return candidates, nil
}

func (sm *CacheSharingManager) calculateSimilarity(entry *SharedCacheEntry, targetSignature string, targetTags []string, targetDeps []string) float64 {
	if entry.DepSignature == targetSignature {
		return 1.0
	}

	tagMatches := 0
	targetTagMap := make(map[string]bool)
	for _, tag := range targetTags {
		targetTagMap[tag] = true
	}
	for _, tag := range entry.Tags {
		if targetTagMap[tag] {
			tagMatches++
		}
	}

	tagScore := float64(tagMatches) / float64(len(targetTags)+1)

	depOverlap := 0
	targetDepMap := make(map[string]bool)
	for _, dep := range targetDeps {
		targetDepMap[dep] = true
	}
	for _, dep := range entry.Deps {
		if targetDepMap[dep] {
			depOverlap++
		}
	}

	depScore := float64(depOverlap) / float64(len(targetDeps)+1)

	return tagScore*0.3 + depScore*0.7
}

func (sm *CacheSharingManager) GetBestMatch(ctx context.Context, projectType string, deps []string) (*SharedCacheEntry, error) {
	candidates, err := sm.FindSimilarCaches(ctx, projectType, deps)
	if err != nil {
		return nil, err
	}

	if len(candidates) == 0 {
		return nil, nil
	}

	return candidates[0], nil
}

func (sm *CacheSharingManager) IncrementHitCount(ctx context.Context, cacheKey string) error {
	registry, err := sm.loadRegistry(ctx)
	if err != nil {
		return err
	}

	if entry, ok := registry.Entries[cacheKey]; ok {
		entry.HitCount++
		return sm.saveRegistry(ctx, registry)
	}

	return nil
}

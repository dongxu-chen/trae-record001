package cache

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type CacheHitRecord struct {
	Key          string    `json:"key"`
	Hit          bool      `json:"hit"`
	Timestamp    time.Time `json:"timestamp"`
	Duration     int64     `json:"duration_ns"`
	Size         int64     `json:"size"`
	ProjectID    string    `json:"project_id"`
	ProjectType  string    `json:"project_type"`
}

type CacheStats struct {
	TotalHits      int64            `json:"total_hits"`
	TotalMisses    int64            `json:"total_misses"`
	TotalSavedTime int64            `json:"total_saved_time_ns"`
	HitRate        float64          `json:"hit_rate"`
	ByKey          map[string]*KeyStats `json:"by_key"`
	ByProject      map[string]*ProjectStats `json:"by_project"`
}

type KeyStats struct {
	Key           string  `json:"key"`
	Hits          int64   `json:"hits"`
	Misses        int64   `json:"misses"`
	HitRate       float64 `json:"hit_rate"`
	TotalSavedTime int64  `json:"total_saved_time_ns"`
	AvgSize       int64   `json:"avg_size"`
	LastAccessed  time.Time `json:"last_accessed"`
}

type ProjectStats struct {
	ProjectID     string  `json:"project_id"`
	ProjectType   string  `json:"project_type"`
	Hits          int64   `json:"hits"`
	Misses        int64   `json:"misses"`
	HitRate       float64 `json:"hit_rate"`
	TotalSavedTime int64  `json:"total_saved_time_ns"`
}

type Analytics struct {
	records    []CacheHitRecord
	stats      CacheStats
	statsFile  string
	mu         sync.RWMutex
	maxRecords int
}

func NewAnalytics(cacheDir string) *Analytics {
	statsFile := filepath.Join(cacheDir, "analytics.json")
	a := &Analytics{
		records:    make([]CacheHitRecord, 0),
		statsFile:  statsFile,
		maxRecords: 10000,
	}
	a.stats.ByKey = make(map[string]*KeyStats)
	a.stats.ByProject = make(map[string]*ProjectStats)
	a.load()
	return a
}

func (a *Analytics) RecordHit(key string, size int64, duration int64, projectID string, projectType string) {
	a.mu.Lock()
	defer a.mu.Unlock()

	record := CacheHitRecord{
		Key:         key,
		Hit:         true,
		Timestamp:   time.Now(),
		Duration:    duration,
		Size:        size,
		ProjectID:   projectID,
		ProjectType: projectType,
	}

	a.addRecord(record)
	a.updateStats(record)
}

func (a *Analytics) RecordMiss(key string, projectID string, projectType string) {
	a.mu.Lock()
	defer a.mu.Unlock()

	record := CacheHitRecord{
		Key:         key,
		Hit:         false,
		Timestamp:   time.Now(),
		ProjectID:   projectID,
		ProjectType: projectType,
	}

	a.addRecord(record)
	a.updateStats(record)
}

func (a *Analytics) addRecord(record CacheHitRecord) {
	a.records = append(a.records, record)
	if len(a.records) > a.maxRecords {
		a.records = a.records[1:]
	}
}

func (a *Analytics) updateStats(record CacheHitRecord) {
	if record.Hit {
		a.stats.TotalHits++
		estimatedSaveTime := estimateSaveTime(record.Size)
		a.stats.TotalSavedTime += estimatedSaveTime
	} else {
		a.stats.TotalMisses++
	}

	total := a.stats.TotalHits + a.stats.TotalMisses
	if total > 0 {
		a.stats.HitRate = float64(a.stats.TotalHits) / float64(total)
	}

	if _, ok := a.stats.ByKey[record.Key]; !ok {
		a.stats.ByKey[record.Key] = &KeyStats{Key: record.Key}
	}
	keyStats := a.stats.ByKey[record.Key]
	keyStats.LastAccessed = record.Timestamp

	if record.Hit {
		keyStats.Hits++
		keyStats.TotalSavedTime += estimateSaveTime(record.Size)
		keyStats.AvgSize = (keyStats.AvgSize*(keyStats.Hits-1) + record.Size) / keyStats.Hits
	} else {
		keyStats.Misses++
	}

	keyTotal := keyStats.Hits + keyStats.Misses
	if keyTotal > 0 {
		keyStats.HitRate = float64(keyStats.Hits) / float64(keyTotal)
	}

	if record.ProjectID != "" {
		if _, ok := a.stats.ByProject[record.ProjectID]; !ok {
			a.stats.ByProject[record.ProjectID] = &ProjectStats{
				ProjectID:   record.ProjectID,
				ProjectType: record.ProjectType,
			}
		}
		projStats := a.stats.ByProject[record.ProjectID]
		if record.Hit {
			projStats.Hits++
			projStats.TotalSavedTime += estimateSaveTime(record.Size)
		} else {
			projStats.Misses++
		}
		projTotal := projStats.Hits + projStats.Misses
		if projTotal > 0 {
			projStats.HitRate = float64(projStats.Hits) / float64(projTotal)
		}
	}
}

func estimateSaveTime(size int64) int64 {
	downloadSpeed := int64(100 * 1024 * 1024)
	if size == 0 {
		size = 100 * 1024 * 1024
	}
	return (size / downloadSpeed) * int64(time.Second)
}

func (a *Analytics) GetStats() CacheStats {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.stats
}

func (a *Analytics) GetKeyStats(key string) *KeyStats {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.stats.ByKey[key]
}

func (a *Analytics) GetTopKeys(limit int) []*KeyStats {
	a.mu.RLock()
	defer a.mu.RUnlock()

	keys := make([]*KeyStats, 0, len(a.stats.ByKey))
	for _, ks := range a.stats.ByKey {
		keys = append(keys, ks)
	}

	for i := 0; i < len(keys); i++ {
		for j := i + 1; j < len(keys); j++ {
			if keys[j].Hits > keys[i].Hits {
				keys[i], keys[j] = keys[j], keys[i]
			}
		}
	}

	if limit > 0 && len(keys) > limit {
		keys = keys[:limit]
	}
	return keys
}

func (a *Analytics) GetRecentRecords(limit int) []CacheHitRecord {
	a.mu.RLock()
	defer a.mu.RUnlock()

	start := 0
	if len(a.records) > limit {
		start = len(a.records) - limit
	}
	records := make([]CacheHitRecord, len(a.records)-start)
	copy(records, a.records[start:])
	return records
}

func (a *Analytics) Save() error {
	a.mu.RLock()
	defer a.mu.RUnlock()

	data := struct {
		Records []CacheHitRecord `json:"records"`
		Stats   CacheStats       `json:"stats"`
	}{
		Records: a.records,
		Stats:   a.stats,
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(a.statsFile, jsonData, 0644)
}

func (a *Analytics) load() {
	data, err := os.ReadFile(a.statsFile)
	if err != nil {
		return
	}

	var loaded struct {
		Records []CacheHitRecord `json:"records"`
		Stats   CacheStats       `json:"stats"`
	}

	if err := json.Unmarshal(data, &loaded); err != nil {
		return
	}

	a.records = loaded.Records
	if loaded.Stats.ByKey == nil {
		loaded.Stats.ByKey = make(map[string]*KeyStats)
	}
	if loaded.Stats.ByProject == nil {
		loaded.Stats.ByProject = make(map[string]*ProjectStats)
	}
	a.stats = loaded.Stats
}

func (a *Analytics) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.records = make([]CacheHitRecord, 0)
	a.stats = CacheStats{
		ByKey:     make(map[string]*KeyStats),
		ByProject: make(map[string]*ProjectStats),
	}
}

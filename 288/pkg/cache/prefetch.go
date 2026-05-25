package cache

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	"github.com/cicache/pkg/storage"
)

type CachePredictor struct {
	storage     storage.Storage
	cacheDir    string
	historyFile string
	history     *UsageHistory
	mu          sync.RWMutex
	maxHistory  int
}

type UsageHistory struct {
	Records []UsageRecord `json:"records"`
}

type UsageRecord struct {
	CacheKey    string    `json:"cache_key"`
	ProjectID   string    `json:"project_id"`
	ProjectType string    `json:"project_type"`
	UsedAt      time.Time `json:"used_at"`
	Branch      string    `json:"branch"`
	CommitHash  string    `json:"commit_hash"`
	Size        int64     `json:"size"`
}

type Prediction struct {
	CacheKey     string  `json:"cache_key"`
	Probability  float64 `json:"probability"`
	ProjectType  string  `json:"project_type"`
	EstimatedSize int64  `json:"estimated_size"`
}

type PrefetchManager struct {
	cacheManager *Manager
	predictor    *CachePredictor
	sharingMgr   *CacheSharingManager
	parallelism  int
}

func NewCachePredictor(store storage.Storage, cacheDir string) *CachePredictor {
	historyFile := filepath.Join(cacheDir, "usage_history.json")
	p := &CachePredictor{
		storage:     store,
		cacheDir:    cacheDir,
		historyFile: historyFile,
		maxHistory:  1000,
	}
	p.history = &UsageHistory{
		Records: make([]UsageRecord, 0),
	}
	p.load()
	return p
}

func (p *CachePredictor) load() {
	data, err := os.ReadFile(p.historyFile)
	if err != nil {
		return
	}

	var history UsageHistory
	if err := json.Unmarshal(data, &history); err != nil {
		return
	}

	p.history = &history
}

func (p *CachePredictor) save() error {
	p.mu.RLock()
	defer p.mu.RUnlock()

	data, err := json.MarshalIndent(p.history, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(p.historyFile, data, 0644)
}

func (p *CachePredictor) RecordUsage(record UsageRecord) {
	p.mu.Lock()
	defer p.mu.Unlock()

	record.UsedAt = time.Now()
	p.history.Records = append(p.history.Records, record)

	if len(p.history.Records) > p.maxHistory {
		p.history.Records = p.history.Records[len(p.history.Records)-p.maxHistory:]
	}

	p.save()
}

func (p *CachePredictor) Predict(projectID string, projectType string, branch string, limit int) []Prediction {
	p.mu.RLock()
	defer p.mu.RUnlock()

	cacheFrequency := make(map[string]int)
	cacheLastUsed := make(map[string]time.Time)
	cacheSize := make(map[string]int64)

	now := time.Now()
	for _, record := range p.history.Records {
		if record.ProjectID == projectID || record.ProjectType == projectType {
			cacheFrequency[record.CacheKey]++
			if record.UsedAt.After(cacheLastUsed[record.CacheKey]) {
				cacheLastUsed[record.CacheKey] = record.UsedAt
			}
			cacheSize[record.CacheKey] = record.Size
		}
	}

	predictions := make([]Prediction, 0, len(cacheFrequency))
	for key, freq := range cacheFrequency {
		recency := now.Sub(cacheLastUsed[key]).Hours()
		recencyScore := 1.0 / (1.0 + recency/24.0)
		frequencyScore := float64(freq) / float64(len(p.history.Records)+1)
		probability := recencyScore*0.6 + frequencyScore*0.4

		predictions = append(predictions, Prediction{
			CacheKey:      key,
			Probability:   probability,
			ProjectType:   projectType,
			EstimatedSize: cacheSize[key],
		})
	}

	sort.Slice(predictions, func(i, j int) bool {
		return predictions[i].Probability > predictions[j].Probability
	})

	if limit > 0 && len(predictions) > limit {
		predictions = predictions[:limit]
	}

	return predictions
}

func (p *CachePredictor) GetRecentHistory(limit int) []UsageRecord {
	p.mu.RLock()
	defer p.mu.RUnlock()

	start := 0
	if len(p.history.Records) > limit {
		start = len(p.history.Records) - limit
	}

	records := make([]UsageRecord, len(p.history.Records)-start)
	copy(records, p.history.Records[start:])
	return records
}

func NewPrefetchManager(cm *Manager, store storage.Storage, cacheDir string, parallelism int) *PrefetchManager {
	if parallelism <= 0 {
		parallelism = 3
	}

	return &PrefetchManager{
		cacheManager: cm,
		predictor:    NewCachePredictor(store, cacheDir),
		sharingMgr:   NewCacheSharingManager(store, cacheDir),
		parallelism:  parallelism,
	}
}

func (pm *PrefetchManager) RecordUsage(cacheKey string, projectID string, projectType string, size int64) {
	pm.predictor.RecordUsage(UsageRecord{
		CacheKey:    cacheKey,
		ProjectID:   projectID,
		ProjectType: projectType,
		Size:        size,
	})
}

func (pm *PrefetchManager) PredictAndPrefetch(ctx context.Context, projectID string, projectType string, branch string, targetPath string) ([]Prediction, error) {
	predictions := pm.predictor.Predict(projectID, projectType, branch, 10)

	if len(predictions) == 0 {
		matches, err := pm.sharingMgr.FindSimilarCaches(ctx, projectType, []string{})
		if err != nil {
			return nil, err
		}
		for _, match := range matches {
			predictions = append(predictions, Prediction{
				CacheKey:      match.CacheKey,
				Probability:   0.5,
				ProjectType:   match.ProjectType,
				EstimatedSize: match.Size,
			})
		}
	}

	semaphore := make(chan struct{}, pm.parallelism)
	var wg sync.WaitGroup

	for i := range predictions {
		semaphore <- struct{}{}
		wg.Add(1)

		go func(idx int) {
			defer wg.Done()
			defer func() { <-semaphore }()

			pred := predictions[idx]
			exists, _ := pm.cacheManager.Exists(ctx, pred.CacheKey)
			if !exists {
				_, err := pm.cacheManager.Download(ctx, pred.CacheKey, targetPath)
				if err != nil {
					return
				}
			}
		}(i)
	}

	wg.Wait()

	return predictions, nil
}

func (pm *PrefetchManager) GetPredictions(projectID string, projectType string, branch string, limit int) []Prediction {
	return pm.predictor.Predict(projectID, projectType, branch, limit)
}

func (pm *PrefetchManager) GetPredictor() *CachePredictor {
	return pm.predictor
}

func (pm *PrefetchManager) GetSharingManager() *CacheSharingManager {
	return pm.sharingMgr
}

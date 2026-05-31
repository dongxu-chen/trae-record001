package cache

import (
	"context"
	"sort"
	"sync"
	"time"

	"github.com/jenkins-cache-sharing/internal/model"
	"go.uber.org/zap"
)

type HitAnalysis struct {
	meta    *MetaStore
	records []*model.CacheHitRecord
	mu      sync.RWMutex
	logger  *zap.Logger
}

func NewHitAnalysis(meta *MetaStore, logger *zap.Logger) *HitAnalysis {
	return &HitAnalysis{
		meta:    meta,
		records: make([]*model.CacheHitRecord, 0),
		logger:  logger,
	}
}

func (ha *HitAnalysis) RecordHit(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	buildNumber int,
	stage model.BuildStage,
	hit bool,
	requestedKey string,
	matchedEntry string,
	dependencyHash string,
	source string,
	latencyMs int64,
	sizeSaved int64,
) *model.CacheHitRecord {
	ha.mu.Lock()
	defer ha.mu.Unlock()

	record := &model.CacheHitRecord{
		ID:             generateID(),
		CacheType:      cacheType,
		JobName:        jobName,
		BuildNumber:    buildNumber,
		Stage:          stage,
		Hit:            hit,
		RequestedKey:   requestedKey,
		MatchedEntry:   matchedEntry,
		DependencyHash: dependencyHash,
		Source:         source,
		LatencyMs:      latencyMs,
		SizeSaved:      sizeSaved,
		CreatedAt:      time.Now(),
	}

	ha.records = append(ha.records, record)

	ha.logger.Debug("recorded cache hit",
		zap.String("job", jobName),
		zap.String("stage", string(stage)),
		zap.Bool("hit", hit),
		zap.String("cache_type", string(cacheType)),
		zap.Int64("latency_ms", latencyMs),
	)

	return record
}

func (ha *HitAnalysis) GetRecords(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	stage model.BuildStage,
	startTime, endTime time.Time,
) []*model.CacheHitRecord {
	ha.mu.RLock()
	defer ha.mu.RUnlock()

	var result []*model.CacheHitRecord
	for _, r := range ha.records {
		if cacheType != "" && r.CacheType != cacheType {
			continue
		}
		if jobName != "" && r.JobName != jobName {
			continue
		}
		if stage != "" && r.Stage != stage {
			continue
		}
		if !startTime.IsZero() && r.CreatedAt.Before(startTime) {
			continue
		}
		if !endTime.IsZero() && r.CreatedAt.After(endTime) {
			continue
		}
		result = append(result, r)
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].CreatedAt.After(result[j].CreatedAt)
	})

	return result
}

func (ha *HitAnalysis) GetHitRateStats(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	timeRange string,
) *model.HitRateStats {
	ha.mu.RLock()
	defer ha.mu.RUnlock()

	var startTime, endTime time.Time
	endTime = time.Now()

	switch timeRange {
	case "1h":
		startTime = endTime.Add(-1 * time.Hour)
	case "24h":
		startTime = endTime.Add(-24 * time.Hour)
	case "7d":
		startTime = endTime.Add(-7 * 24 * time.Hour)
	case "30d":
		startTime = endTime.Add(-30 * 24 * time.Hour)
	default:
		startTime = time.Time{}
	}

	stageMap := make(map[model.BuildStage]*model.StageHitRate)
	var totalRequests int64
	var totalHits int64
	var totalTimeSaved int64
	var totalSizeSaved int64

	for _, r := range ha.records {
		if cacheType != "" && r.CacheType != cacheType {
			continue
		}
		if jobName != "" && r.JobName != jobName {
			continue
		}
		if !startTime.IsZero() && r.CreatedAt.Before(startTime) {
			continue
		}

		totalRequests++
		if r.Hit {
			totalHits++
			totalTimeSaved += r.LatencyMs
			totalSizeSaved += r.SizeSaved
		}

		stage, ok := stageMap[r.Stage]
		if !ok {
			stage = &model.StageHitRate{Stage: r.Stage}
			stageMap[r.Stage] = stage
		}
		stage.Total++
		if r.Hit {
			stage.Hits++
			stage.TimeSaved += r.LatencyMs
			stage.SizeSaved += r.SizeSaved
		}
	}

	stages := make([]model.StageHitRate, 0, len(stageMap))
	for _, s := range stageMap {
		if s.Total > 0 {
			s.HitRate = float64(s.Hits) / float64(s.Total)
		}
		stages = append(stages, *s)
	}

	sort.Slice(stages, func(i, j int) bool {
		return stages[i].Stage < stages[j].Stage
	})

	overallHitRate := 0.0
	if totalRequests > 0 {
		overallHitRate = float64(totalHits) / float64(totalRequests)
	}

	return &model.HitRateStats{
		CacheType:      cacheType,
		JobName:        jobName,
		TimeRange:      timeRange,
		TotalRequests:  totalRequests,
		TotalHits:      totalHits,
		OverallHitRate: overallHitRate,
		ByStage:        stages,
		StartTime:      startTime,
		EndTime:        endTime,
	}
}

func (ha *HitAnalysis) GetTopMissedKeys(
	ctx context.Context,
	cacheType model.CacheType,
	jobName string,
	limit int,
) map[string]int64 {
	ha.mu.RLock()
	defer ha.mu.RUnlock()

	missed := make(map[string]int64)
	for _, r := range ha.records {
		if r.Hit {
			continue
		}
		if cacheType != "" && r.CacheType != cacheType {
			continue
		}
		if jobName != "" && r.JobName != jobName {
			continue
		}
		missed[r.RequestedKey]++
	}

	return missed
}

func (ha *HitAnalysis) CleanOldRecords(ctx context.Context, maxAge time.Duration) int {
	ha.mu.Lock()
	defer ha.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	var remaining []*model.CacheHitRecord
	removed := 0

	for _, r := range ha.records {
		if r.CreatedAt.After(cutoff) {
			remaining = append(remaining, r)
		} else {
			removed++
		}
	}

	ha.records = remaining
	ha.logger.Info("cleaned old hit records", zap.Int("removed", removed))
	return removed
}

func (ha *HitAnalysis) GetRecordsByBuild(
	ctx context.Context,
	jobName string,
	buildNumber int,
) []*model.CacheHitRecord {
	ha.mu.RLock()
	defer ha.mu.RUnlock()

	var result []*model.CacheHitRecord
	for _, r := range ha.records {
		if r.JobName == jobName && r.BuildNumber == buildNumber {
			result = append(result, r)
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].CreatedAt.Before(result[j].CreatedAt)
	})

	return result
}

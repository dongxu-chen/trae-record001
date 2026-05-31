package cache

import (
	"context"
	"fmt"
	"sort"
	"time"

	"github.com/jenkins-cache-sharing/internal/model"
	"github.com/robfig/cron/v3"
	"go.uber.org/zap"
)

type CleanupEngine struct {
	meta     *MetaStore
	vm       *VersionManager
	policies map[string]*model.CleanupPolicy
	results  []*model.CleanupResult
	cron     *cron.Cron
	logger   *zap.Logger
}

func NewCleanupEngine(meta *MetaStore, vm *VersionManager, logger *zap.Logger) *CleanupEngine {
	ce := &CleanupEngine{
		meta:     meta,
		vm:       vm,
		policies: make(map[string]*model.CleanupPolicy),
		results:  make([]*model.CleanupResult, 0),
		cron:     cron.New(cron.WithSeconds()),
		logger:   logger,
	}

	ce.addDefaultPolicies()

	return ce
}

func (ce *CleanupEngine) addDefaultPolicies() {
	ce.policies["default-lru-size"] = &model.CleanupPolicy{
		ID:             "default-lru-size",
		Name:           "Default LRU + Size Cleanup",
		CacheTypes:     []model.CacheType{model.CacheTypeMaven, model.CacheTypeNPM, model.CacheTypeGradle},
		MaxAge:         7 * 24 * time.Hour,
		MaxSize:        20 << 30,
		MaxVersions:    5,
		KeepLatest:     2,
		Strategy:       model.CleanupStrategyLRUSize,
		LRUWeight:      0.6,
		SizeWeight:     0.4,
		Enabled:        true,
		CronExpression: "0 0 2 * * *",
		CreatedAt:      time.Now(),
	}

	ce.policies["maven-lru-size"] = &model.CleanupPolicy{
		ID:             "maven-lru-size",
		Name:           "Maven LRU + Size Cleanup",
		CacheTypes:     []model.CacheType{model.CacheTypeMaven},
		MaxAge:         14 * 24 * time.Hour,
		MaxSize:        10 << 30,
		MaxVersions:    10,
		KeepLatest:     3,
		Strategy:       model.CleanupStrategyLRUSize,
		LRUWeight:      0.5,
		SizeWeight:     0.5,
		Enabled:        true,
		CronExpression: "0 0 3 * * *",
		CreatedAt:      time.Now(),
	}

	ce.policies["npm-lru-size"] = &model.CleanupPolicy{
		ID:             "npm-lru-size",
		Name:           "NPM LRU + Size Cleanup",
		CacheTypes:     []model.CacheType{model.CacheTypeNPM},
		MaxAge:         5 * 24 * time.Hour,
		MaxSize:        5 << 30,
		MaxVersions:    8,
		KeepLatest:     2,
		Strategy:       model.CleanupStrategyLRUSize,
		LRUWeight:      0.7,
		SizeWeight:     0.3,
		Enabled:        true,
		CronExpression: "0 0 4 * * *",
		CreatedAt:      time.Now(),
	}

	ce.policies["gradle-lru-size"] = &model.CleanupPolicy{
		ID:             "gradle-lru-size",
		Name:           "Gradle LRU + Size Cleanup",
		CacheTypes:     []model.CacheType{model.CacheTypeGradle},
		MaxAge:         10 * 24 * time.Hour,
		MaxSize:        8 << 30,
		MaxVersions:    8,
		KeepLatest:     2,
		Strategy:       model.CleanupStrategyLRUSize,
		LRUWeight:      0.55,
		SizeWeight:     0.45,
		Enabled:        true,
		CronExpression: "0 0 5 * * *",
		CreatedAt:      time.Now(),
	}
}

func (ce *CleanupEngine) Start() error {
	for _, policy := range ce.policies {
		if policy.Enabled {
			if err := ce.schedulePolicy(policy); err != nil {
				ce.logger.Error("failed to schedule policy",
					zap.String("policy_id", policy.ID),
					zap.Error(err),
				)
			}
		}
	}

	ce.cron.Start()
	ce.logger.Info("cleanup engine started with LRU + Size strategies")
	return nil
}

func (ce *CleanupEngine) Stop() {
	ce.cron.Stop()
	ce.logger.Info("cleanup engine stopped")
}

func (ce *CleanupEngine) schedulePolicy(policy *model.CleanupPolicy) error {
	p := policy
	_, err := ce.cron.AddFunc(policy.CronExpression, func() {
		ctx := context.Background()
		ce.logger.Info("running scheduled cleanup", zap.String("policy_id", p.ID))
		if _, err := ce.ExecutePolicy(ctx, p.ID); err != nil {
			ce.logger.Error("scheduled cleanup failed",
				zap.String("policy_id", p.ID),
				zap.Error(err),
			)
		}
	})
	return err
}

func (ce *CleanupEngine) ExecutePolicy(ctx context.Context, policyID string) (*model.CleanupResult, error) {
	policy, ok := ce.policies[policyID]
	if !ok {
		return nil, fmt.Errorf("policy not found: %s", policyID)
	}

	result := &model.CleanupResult{
		PolicyID:   policyID,
		RemovedIDs: []string{},
		StartedAt:  time.Now(),
		Errors:     []string{},
	}

	ce.meta.mu.Lock()
	defer ce.meta.mu.Unlock()

	for _, cacheType := range policy.CacheTypes {
		ce.cleanupByTypeLRUSize(ctx, cacheType, policy, result)
	}

	result.FinishedAt = time.Now()
	now := time.Now()
	policy.LastRunAt = &now

	ce.results = append(ce.results, result)

	if err := ce.meta.save(); err != nil {
		ce.logger.Error("failed to save metadata after cleanup", zap.Error(err))
	}

	ce.logger.Info("cleanup policy executed",
		zap.String("policy_id", policyID),
		zap.String("strategy", string(policy.Strategy)),
		zap.Int("removed", len(result.RemovedIDs)),
		zap.Int64("freed_bytes", result.FreedBytes),
	)

	return result, nil
}

func (ce *CleanupEngine) cleanupByTypeLRUSize(
	ctx context.Context,
	cacheType model.CacheType,
	policy *model.CleanupPolicy,
	result *model.CleanupResult,
) {
	var allEntries []*model.CacheEntry
	for _, entry := range ce.meta.entries {
		if entry.Type == cacheType && entry.Status == model.CacheStatusActive {
			allEntries = append(allEntries, entry)
		}
	}

	if len(allEntries) == 0 {
		return
	}

	groupedByJob := make(map[string][]*model.CacheEntry)
	for _, entry := range allEntries {
		groupedByJob[entry.JobName] = append(groupedByJob[entry.JobName], entry)
	}

	var protectedIDs map[string]bool = make(map[string]bool)
	for jobName, jobEntries := range groupedByJob {
		sort.Slice(jobEntries, func(i, j int) bool {
			return jobEntries[i].CreatedAt.After(jobEntries[j].CreatedAt)
		})

		for i := 0; i < policy.KeepLatest && i < len(jobEntries); i++ {
			protectedIDs[jobEntries[i].ID] = true
		}

		ce.logger.Debug("protected entries for job",
			zap.String("job", jobName),
			zap.Int("protected", policy.KeepLatest),
		)
	}

	var remainingEntries []*model.CacheEntry
	var currentTotalSize int64
	for _, entry := range allEntries {
		if !protectedIDs[entry.ID] {
			remainingEntries = append(remainingEntries, entry)
		}
		currentTotalSize += entry.Size
	}

	ce.logger.Debug("cleanup phase 1: age-based eviction",
		zap.String("type", string(cacheType)),
		zap.Int("total_entries", len(allEntries)),
		zap.Int("protected", len(protectedIDs)),
		zap.Int("candidates", len(remainingEntries)),
		zap.Int64("current_size", currentTotalSize),
		zap.Int64("max_size", policy.MaxSize),
	)

	now := time.Now()
	var afterAgeFilter []*model.CacheEntry
	for _, entry := range remainingEntries {
		if policy.MaxAge > 0 && now.Sub(entry.CreatedAt) > policy.MaxAge {
			result.RemovedIDs = append(result.RemovedIDs, entry.ID)
			result.FreedBytes += entry.Size
			entry.Status = model.CacheStatusDeleting
			ce.logger.Debug("evicted by age",
				zap.String("id", entry.ID),
				zap.Duration("age", now.Sub(entry.CreatedAt)),
				zap.Duration("max_age", policy.MaxAge),
			)
		} else {
			afterAgeFilter = append(afterAgeFilter, entry)
		}
	}

	ce.logger.Debug("cleanup phase 2: size-based eviction",
		zap.Int("removed_by_age", len(result.RemovedIDs)),
		zap.Int64("freed_by_age", result.FreedBytes),
	)

	var afterVersionFilter []*model.CacheEntry
	for jobName, jobEntries := range groupedByJob {
		var unprotected []*model.CacheEntry
		for _, e := range jobEntries {
			if !protectedIDs[e.ID] {
				unprotected = append(unprotected, e)
			}
		}

		if len(unprotected) > policy.MaxVersions {
			sort.Slice(unprotected, func(i, j int) bool {
				return unprotected[i].CreatedAt.Before(unprotected[j].CreatedAt)
			})

			removeCount := len(unprotected) - policy.MaxVersions
			for i := 0; i < removeCount; i++ {
				entry := unprotected[i]
				if entry.Status == model.CacheStatusDeleting {
					continue
				}
				result.RemovedIDs = append(result.RemovedIDs, entry.ID)
				result.FreedBytes += entry.Size
				entry.Status = model.CacheStatusDeleting
				ce.logger.Debug("evicted by version limit",
					zap.String("id", entry.ID),
					zap.String("job", jobName),
					zap.Int("version_count", len(unprotected)),
					zap.Int("max_versions", policy.MaxVersions),
				)
			}
		}
	}

	for _, entry := range afterAgeFilter {
		if entry.Status != model.CacheStatusDeleting {
			afterVersionFilter = append(afterVersionFilter, entry)
		}
	}

	ce.logger.Debug("cleanup phase 3: LRU + size eviction",
		zap.Int("remaining_after_age", len(afterAgeFilter)),
		zap.Int("removed_by_version", len(result.RemovedIDs)),
	)

	if policy.MaxSize > 0 && currentTotalSize > policy.MaxSize {
		targetSize := policy.MaxSize
		remainingSize := currentTotalSize - result.FreedBytes
		needToFree := remainingSize - targetSize

		if needToFree > 0 {
			ce.logger.Info("size limit exceeded, starting LRU eviction",
				zap.Int64("current_size", remainingSize),
				zap.Int64("max_size", targetSize),
				zap.Int64("need_to_free", needToFree),
				zap.String("strategy", string(policy.Strategy)),
				zap.Float64("lru_weight", policy.LRUWeight),
				zap.Float64("size_weight", policy.SizeWeight),
			)

			ce.applyLRUSizeEviction(afterVersionFilter, policy, needToFree, result)
		}
	}
}

func (ce *CleanupEngine) applyLRUSizeEviction(
	entries []*model.CacheEntry,
	policy *model.CleanupPolicy,
	needToFree int64,
	result *model.CleanupResult,
) {
	type scoredEntry struct {
		entry *model.CacheEntry
		score float64
	}

	now := time.Now()
	var scored []scoredEntry

	for _, entry := range entries {
		if entry.Status == model.CacheStatusDeleting {
			continue
		}

		score := ce.computeLRUSizeScore(entry, policy, now)
		scored = append(scored, scoredEntry{
			entry: entry,
			score: score,
		})
	}

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})

	ce.logger.Debug("eviction scoring",
		zap.Int("candidates", len(scored)),
	)

	var freed int64
	for _, se := range scored {
		if freed >= needToFree {
			break
		}

		if se.entry.Status == model.CacheStatusDeleting {
			continue
		}

		se.entry.Status = model.CacheStatusDeleting
		result.RemovedIDs = append(result.RemovedIDs, se.entry.ID)
		result.FreedBytes += se.entry.Size
		freed += se.entry.Size

		ce.logger.Debug("evicted by LRU+size",
			zap.String("id", se.entry.ID),
			zap.Float64("score", se.score),
			zap.Int64("size", se.entry.Size),
			zap.Int64("cumulative_freed", freed),
		)
	}

	if freed < needToFree {
		ce.logger.Warn("could not free enough space",
			zap.Int64("freed", freed),
			zap.Int64("target", needToFree),
			zap.Int64("shortage", needToFree-freed),
		)
	} else {
		ce.logger.Info("LRU+size eviction complete",
			zap.Int64("freed", freed),
			zap.Int64("target", needToFree),
		)
	}
}

func (ce *CleanupEngine) computeLRUSizeScore(
	entry *model.CacheEntry,
	policy *model.CleanupPolicy,
	now time.Time,
) float64 {
	var lastAccess time.Time
	if entry.LastAccess != nil {
		lastAccess = *entry.LastAccess
	} else {
		lastAccess = entry.CreatedAt
	}

	hoursSinceAccess := now.Sub(lastAccess).Hours()
	maxHours := 24 * 30.0
	if hoursSinceAccess > maxHours {
		hoursSinceAccess = maxHours
	}
	lruScore := hoursSinceAccess / maxHours

	maxSize := 1 << 30.0
	sizeMB := float64(entry.Size) / (1024 * 1024)
	sizeScore := sizeMB / 1024.0
	if sizeScore > 1.0 {
		sizeScore = 1.0
	}

	compositeScore := lruScore*policy.LRUWeight + sizeScore*policy.SizeWeight

	ce.logger.Debug("entry score calculation",
		zap.String("id", entry.ID),
		zap.Float64("hours_since", hoursSinceAccess),
		zap.Float64("lru_score", lruScore),
		zap.Float64("size_mb", sizeMB),
		zap.Float64("size_score", sizeScore),
		zap.Float64("composite", compositeScore),
	)

	return compositeScore
}

func (ce *CleanupEngine) CheckSizeAndEvict(ctx context.Context, cacheType model.CacheType, maxSize int64) (*model.CleanupResult, error) {
	result := &model.CleanupResult{
		PolicyID:   "on-demand-eviction",
		RemovedIDs: []string{},
		StartedAt:  time.Now(),
		Errors:     []string{},
	}

	ce.meta.mu.Lock()
	defer ce.meta.mu.Unlock()

	var currentSize int64
	var allEntries []*model.CacheEntry
	for _, entry := range ce.meta.entries {
		if entry.Status != model.CacheStatusActive {
			continue
		}
		if cacheType != "" && entry.Type != cacheType {
			continue
		}
		currentSize += entry.Size
		allEntries = append(allEntries, entry)
	}

	if currentSize <= maxSize {
		result.FinishedAt = time.Now()
		ce.logger.Debug("no eviction needed",
			zap.Int64("current", currentSize),
			zap.Int64("max", maxSize),
		)
		return result, nil
	}

	needToFree := currentSize - maxSize

	now := time.Now()
	sort.Slice(allEntries, func(i, j int) bool {
		iScore := computeLRUScoreInline(allEntries[i], now)
		jScore := computeLRUScoreInline(allEntries[j], now)
		return iScore < jScore
	})

	ce.logger.Info("on-demand eviction triggered",
		zap.Int64("current_size", currentSize),
		zap.Int64("max_size", maxSize),
		zap.Int64("need_to_free", needToFree),
	)

	var protected map[string]bool = make(map[string]bool)
	groupedByJob := make(map[string][]*model.CacheEntry)
	for _, entry := range allEntries {
		groupedByJob[entry.JobName] = append(groupedByJob[entry.JobName], entry)
	}

	for _, jobEntries := range groupedByJob {
		sort.Slice(jobEntries, func(i, j int) bool {
			return jobEntries[i].CreatedAt.After(jobEntries[j].CreatedAt)
		})

		keep := 2
		for i := 0; i < keep && i < len(jobEntries); i++ {
			protected[jobEntries[i].ID] = true
		}
	}

	defaultPolicy := &model.CleanupPolicy{
		LRUWeight:  0.6,
		SizeWeight: 0.4,
	}

	var candidates []*model.CacheEntry
	for _, entry := range allEntries {
		if !protected[entry.ID] && entry.Status == model.CacheStatusActive {
			candidates = append(candidates, entry)
		}
	}

	ce.applyLRUSizeEviction(candidates, defaultPolicy, needToFree, result)

	if err := ce.meta.save(); err != nil {
		ce.logger.Error("failed to save metadata after eviction", zap.Error(err))
	}

	result.FinishedAt = time.Now()
	ce.results = append(ce.results, result)

	return result, nil
}

func computeLRUScoreInline(entry *model.CacheEntry, now time.Time) float64 {
	var lastAccess time.Time
	if entry.LastAccess != nil {
		lastAccess = *entry.LastAccess
	} else {
		lastAccess = entry.CreatedAt
	}
	hoursSince := now.Sub(lastAccess).Hours()
	return hoursSince - float64(entry.AccessCount)*10
}

func (ce *CleanupEngine) CreatePolicy(policy *model.CleanupPolicy) (*model.CleanupPolicy, error) {
	if policy.ID == "" {
		policy.ID = generateID()
	}
	policy.CreatedAt = time.Now()

	if policy.Strategy == "" {
		policy.Strategy = model.CleanupStrategyLRUSize
	}
	if policy.LRUWeight == 0 && policy.SizeWeight == 0 {
		policy.LRUWeight = 0.6
		policy.SizeWeight = 0.4
	}

	ce.policies[policy.ID] = policy

	if policy.Enabled {
		if err := ce.schedulePolicy(policy); err != nil {
			ce.logger.Error("failed to schedule new policy", zap.Error(err))
		}
	}

	ce.logger.Info("created cleanup policy",
		zap.String("id", policy.ID),
		zap.String("strategy", string(policy.Strategy)),
	)
	return policy, nil
}

func (ce *CleanupEngine) UpdatePolicy(id string, updates func(*model.CleanupPolicy)) (*model.CleanupPolicy, error) {
	policy, ok := ce.policies[id]
	if !ok {
		return nil, fmt.Errorf("policy not found: %s", id)
	}

	updates(policy)
	return policy, nil
}

func (ce *CleanupEngine) DeletePolicy(id string) error {
	if _, ok := ce.policies[id]; !ok {
		return fmt.Errorf("policy not found: %s", id)
	}
	delete(ce.policies, id)
	ce.logger.Info("deleted cleanup policy", zap.String("id", id))
	return nil
}

func (ce *CleanupEngine) GetPolicies() []*model.CleanupPolicy {
	var policies []*model.CleanupPolicy
	for _, p := range ce.policies {
		policies = append(policies, p)
	}
	return policies
}

func (ce *CleanupEngine) GetPolicy(id string) (*model.CleanupPolicy, error) {
	policy, ok := ce.policies[id]
	if !ok {
		return nil, fmt.Errorf("policy not found: %s", id)
	}
	return policy, nil
}

func (ce *CleanupEngine) GetResults() []*model.CleanupResult {
	return ce.results
}

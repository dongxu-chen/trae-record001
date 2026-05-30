package planner

import (
	"math"
	"sort"
	"sync"
	"time"

	"heatcache/internal/cache"
)

type CachePlan struct {
	RecommendedMaxMemory    int64
	RecommendedStrategy     cache.InvalidationStrategy
	RecommendedLRUThreshold int
	ExpectedHitRate         float64
	MemoryBreakdown         *MemoryBreakdown
	StrategyComparison      []StrategyScore
	HotDataRatio            float64
	WorkingSetSize          int64
	EvictionRate            float64
}

type MemoryBreakdown struct {
	HotDataSize      int64
	WarmDataSize     int64
	ColdDataSize     int64
	OverheadPerEntry int64
	TotalEntries     int
	AvgEntrySize     int64
}

type StrategyScore struct {
	Strategy    cache.InvalidationStrategy
	Score       float64
	Pros        []string
	Cons        []string
	UseCase     string
}

type EntryStat struct {
	Key        string
	Size       int64
	HitCount   int64
	LastAccess time.Time
	Tables     []string
	TTL        time.Duration
}

type CachePlanner struct {
	entryStats  map[string]*EntryStat
	memoryLimit int64
	mu          sync.RWMutex
}

func NewCachePlanner(memoryLimit int64) *CachePlanner {
	return &CachePlanner{
		entryStats:  make(map[string]*EntryStat),
		memoryLimit: memoryLimit,
	}
}

func (cp *CachePlanner) RecordEntry(entry *EntryStat) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	cp.entryStats[entry.Key] = entry
}

func (cp *CachePlanner) RecordAccess(key string, timestamp time.Time) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	if es, exists := cp.entryStats[key]; exists {
		es.HitCount++
		es.LastAccess = timestamp
	}
}

func (cp *CachePlanner) RemoveEntry(key string) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	delete(cp.entryStats, key)
}

func (cp *CachePlanner) GeneratePlan() *CachePlan {
	cp.mu.RLock()
	defer cp.mu.RUnlock()

	if len(cp.entryStats) == 0 {
		return cp.generateDefaultPlan()
	}

	entries := make([]*EntryStat, 0, len(cp.entryStats))
	for _, e := range cp.entryStats {
		entries = append(entries, e)
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].HitCount > entries[j].HitCount
	})

	workingSet := cp.calculateWorkingSet(entries)
	memoryBreakdown := cp.analyzeMemoryBreakdown(entries)
	strategyScores := cp.evaluateStrategies(entries)
	bestStrategy := strategyScores[0].Strategy
	bestLRUThreshold := cp.calculateOptimalLRUThreshold(entries)
	expectedHitRate := cp.predictHitRate(entries, bestStrategy, bestLRUThreshold)
	hotDataRatio := cp.calculateHotDataRatio(entries)
	evictionRate := cp.estimateEvictionRate(entries)

	return &CachePlan{
		RecommendedMaxMemory:    workingSet * 12 / 10,
		RecommendedStrategy:     bestStrategy,
		RecommendedLRUThreshold: bestLRUThreshold,
		ExpectedHitRate:         expectedHitRate,
		MemoryBreakdown:         memoryBreakdown,
		StrategyComparison:      strategyScores,
		HotDataRatio:            hotDataRatio,
		WorkingSetSize:          workingSet,
		EvictionRate:            evictionRate,
	}
}

func (cp *CachePlanner) generateDefaultPlan() *CachePlan {
	defaultMemory := int64(512 * 1024 * 1024)
	if cp.memoryLimit > 0 {
		defaultMemory = cp.memoryLimit
	}

	return &CachePlan{
		RecommendedMaxMemory:    defaultMemory,
		RecommendedStrategy:     cache.InvalidationHybrid,
		RecommendedLRUThreshold: 10000,
		ExpectedHitRate:         0.5,
		MemoryBreakdown: &MemoryBreakdown{
			OverheadPerEntry: 100,
		},
		StrategyComparison: cp.getDefaultStrategyScores(),
	}
}

func (cp *CachePlanner) calculateWorkingSet(entries []*EntryStat) int64 {
	if len(entries) == 0 {
		return 0
	}

	cutoff := time.Now().Add(-24 * time.Hour)
	var totalSize int64
	var count int

	for _, e := range entries {
		if e.LastAccess.After(cutoff) {
			totalSize += e.Size
			count++
		}
	}

	if totalSize == 0 {
		for _, e := range entries {
			totalSize += e.Size
		}
	}

	_ = count
	return totalSize
}

func (cp *CachePlanner) analyzeMemoryBreakdown(entries []*EntryStat) *MemoryBreakdown {
	breakdown := &MemoryBreakdown{
		TotalEntries: len(entries),
	}

	var totalSize int64
	for _, e := range entries {
		totalSize += e.Size
	}

	if len(entries) > 0 {
		breakdown.AvgEntrySize = totalSize / int64(len(entries))
	}

	if len(entries) >= 100 {
		p20 := len(entries) / 5
		p80 := len(entries) * 4 / 5

		for i, e := range entries {
			if i < p20 {
				breakdown.HotDataSize += e.Size
			} else if i < p80 {
				breakdown.WarmDataSize += e.Size
			} else {
				breakdown.ColdDataSize += e.Size
			}
		}
	} else {
		breakdown.HotDataSize = totalSize
	}

	breakdown.OverheadPerEntry = 64 + 32 + 8 + 8

	return breakdown
}

func (cp *CachePlanner) evaluateStrategies(entries []*EntryStat) []StrategyScore {
	scores := make([]StrategyScore, 0, 4)

	ttlScore := StrategyScore{
		Strategy: cache.InvalidationTTL,
		UseCase:  "数据更新频率低、可接受短暂过期",
		Pros:     []string{"实现简单", "内存开销小", "易于调试"},
		Cons:     []string{"失效不及时", "可能缓存雪崩", "不支持依赖追踪"},
	}
	ttlScore.Score = cp.scoreStrategy(entries, cache.InvalidationTTL)
	scores = append(scores, ttlScore)

	lruScore := StrategyScore{
		Strategy: cache.InvalidationLRU,
		UseCase:  "内存受限、访问模式稳定",
		Pros:     []string{"自动保热", "内存可控", "适合热点稳定"},
		Cons:     []string{"LRU队列开销", "污染问题", "批量扫描慢"},
	}
	lruScore.Score = cp.scoreStrategy(entries, cache.InvalidationLRU)
	scores = append(scores, lruScore)

	depScore := StrategyScore{
		Strategy: cache.InvalidationDependency,
		UseCase:  "表关联强、更新频率高",
		Pros:     []string{"失效精准", "一致性好", "支持细粒度控制"},
		Cons:     []string{"依赖图维护开销", "DDL需处理", "冷启动慢"},
	}
	depScore.Score = cp.scoreStrategy(entries, cache.InvalidationDependency)
	scores = append(scores, depScore)

	hybridScore := StrategyScore{
		Strategy: cache.InvalidationHybrid,
		UseCase:  "通用场景、平衡性能与一致性",
		Pros:     []string{"兼顾LRU保热+依赖失效", "适应性强", "故障降级好"},
		Cons:     []string{"配置复杂", "代码量大", "监控要求高"},
	}
	hybridScore.Score = cp.scoreStrategy(entries, cache.InvalidationHybrid)
	scores = append(scores, hybridScore)

	sort.Slice(scores, func(i, j int) bool {
		return scores[i].Score > scores[j].Score
	})

	return scores
}

func (cp *CachePlanner) scoreStrategy(entries []*EntryStat, strategy cache.InvalidationStrategy) float64 {
	if len(entries) == 0 {
		return 0.5
	}

	hotRatio := cp.calculateHotDataRatio(entries)
	uniqueTables := cp.countUniqueTables(entries)
	avgTTL := cp.averageTTL(entries)
	hitSkew := cp.calculateHitSkew(entries)

	score := 0.0

	switch strategy {
	case cache.InvalidationTTL:
		score = 0.6 - math.Abs(0.3-hotRatio)*0.5
		if avgTTL > 1*time.Hour {
			score += 0.2
		}
		if uniqueTables > 10 {
			score -= 0.2
		}

	case cache.InvalidationLRU:
		score = 0.4 + hitSkew*0.4
		if cp.memoryLimit > 0 && cp.memoryLimit < cp.calculateWorkingSet(entries) {
			score += 0.2
		}
		if uniqueTables > 20 {
			score += 0.1
		}

	case cache.InvalidationDependency:
		score = 0.3 + float64(uniqueTables)/50.0
		if avgTTL < 5*time.Minute {
			score += 0.3
		}
		if hotRatio > 0.3 {
			score -= 0.1
		}

	case cache.InvalidationHybrid:
		score = 0.6 + math.Min(hotRatio, 0.5)*0.4
		if uniqueTables > 5 && uniqueTables < 50 {
			score += 0.1
		}
	}

	return math.Max(0, math.Min(1, score))
}

func (cp *CachePlanner) calculateOptimalLRUThreshold(entries []*EntryStat) int {
	if len(entries) < 10 {
		return 1000
	}

	hotRatio := cp.calculateHotDataRatio(entries)

	memoryPerEntry := cp.estimateAvgEntrySize(entries)
	hotEntries := int(float64(len(entries)) * hotRatio * 1.5)

	if cp.memoryLimit > 0 {
		memoryBased := int(cp.memoryLimit / memoryPerEntry)
		return int(math.Max(float64(memoryBased), float64(hotEntries)))
	}

	return hotEntries
}

func (cp *CachePlanner) predictHitRate(
	entries []*EntryStat,
	strategy cache.InvalidationStrategy,
	lruThreshold int,
) float64 {
	if len(entries) == 0 {
		return 0.5
	}

	hotRatio := cp.calculateHotDataRatio(entries)
	hitSkew := cp.calculateHitSkew(entries)

	baseHitRate := 0.3 + hotRatio*0.5 + hitSkew*0.2

	strategyFactor := 1.0
	switch strategy {
	case cache.InvalidationHybrid:
		strategyFactor = 1.1
	case cache.InvalidationLRU:
		if lruThreshold >= len(entries) {
			strategyFactor = 1.05
		} else if lruThreshold < len(entries)/10 {
			strategyFactor = 0.85
		}
	case cache.InvalidationDependency:
		strategyFactor = 1.05
	}

	return math.Min(0.98, baseHitRate*strategyFactor)
}

func (cp *CachePlanner) calculateHotDataRatio(entries []*EntryStat) float64 {
	if len(entries) == 0 {
		return 0.5
	}

	totalHits := int64(0)
	for _, e := range entries {
		totalHits += e.HitCount
	}
	if totalHits == 0 {
		return 0.3
	}

	hotThreshold := totalHits / 10
	hotEntries := 0
	for _, e := range entries {
		if e.HitCount >= hotThreshold {
			hotEntries++
		}
	}

	return float64(hotEntries) / float64(len(entries))
}

func (cp *CachePlanner) countUniqueTables(entries []*EntryStat) int {
	tables := make(map[string]bool)
	for _, e := range entries {
		for _, t := range e.Tables {
			tables[t] = true
		}
	}
	return len(tables)
}

func (cp *CachePlanner) averageTTL(entries []*EntryStat) time.Duration {
	if len(entries) == 0 {
		return 0
	}
	var total time.Duration
	for _, e := range entries {
		total += e.TTL
	}
	return total / time.Duration(len(entries))
}

func (cp *CachePlanner) calculateHitSkew(entries []*EntryStat) float64 {
	if len(entries) < 2 {
		return 0.5
	}

	hitCounts := make([]float64, len(entries))
	for i, e := range entries {
		hitCounts[i] = float64(e.HitCount)
	}

	mean := 0.0
	for _, h := range hitCounts {
		mean += h
	}
	mean /= float64(len(hitCounts))

	if mean == 0 {
		return 0
	}

	variance := 0.0
	for _, h := range hitCounts {
		diff := h - mean
		variance += diff * diff
	}
	variance /= float64(len(hitCounts))
	stddev := math.Sqrt(variance)

	cv := stddev / mean
	return math.Min(1.0, cv/2.0)
}

func (cp *CachePlanner) estimateAvgEntrySize(entries []*EntryStat) int64 {
	if len(entries) == 0 {
		return 1024
	}
	var total int64
	for _, e := range entries {
		total += e.Size
	}
	return total / int64(len(entries))
}

func (cp *CachePlanner) estimateEvictionRate(entries []*EntryStat) float64 {
	if cp.memoryLimit == 0 {
		return 0.01
	}

	workingSet := cp.calculateWorkingSet(entries)
	if workingSet < cp.memoryLimit {
		return 0.0
	}

	ratio := float64(workingSet) / float64(cp.memoryLimit)
	return math.Min(0.5, ratio*0.1)
}

func (cp *CachePlanner) getDefaultStrategyScores() []StrategyScore {
	return []StrategyScore{
		{
			Strategy: cache.InvalidationHybrid,
			Score:    0.8,
			UseCase:  "通用场景",
			Pros:     []string{"平衡方案", "适应性强"},
			Cons:     []string{"配置较多"},
		},
		{
			Strategy: cache.InvalidationLRU,
			Score:    0.6,
			UseCase:  "内存受限",
			Pros:     []string{"自动保热"},
			Cons:     []string{"LRU开销"},
		},
	}
}

func (cp *CachePlanner) UpdateMemoryLimit(limit int64) {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	cp.memoryLimit = limit
}

func (cp *CachePlanner) GetEntryCount() int {
	cp.mu.RLock()
	defer cp.mu.RUnlock()
	return len(cp.entryStats)
}

func (cp *CachePlanner) Clear() {
	cp.mu.Lock()
	defer cp.mu.Unlock()
	cp.entryStats = make(map[string]*EntryStat)
}

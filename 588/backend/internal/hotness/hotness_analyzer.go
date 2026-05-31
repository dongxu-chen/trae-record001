package hotness

import (
	"log"
	"math"
	"sort"
	"sync"
	"time"
	"zk-inspector/internal/storage"
)

type AccessType string

const (
	AccessRead  AccessType = "read"
	AccessWrite AccessType = "write"
	AccessWatch AccessType = "watch"
)

type AccessRecord struct {
	Timestamp time.Time  `json:"timestamp"`
	Type      AccessType `json:"type"`
	Path      string     `json:"path"`
}

type NodeHotness struct {
	Path            string  `json:"path"`
	ReadCount       int64   `json:"read_count"`
	WriteCount      int64   `json:"write_count"`
	WatchCount      int64   `json:"watch_count"`
	TotalAccess     int64   `json:"total_access"`
	HotnessScore    float64 `json:"hotness_score"`
	LastAccessTime  time.Time `json:"last_access_time"`
	ColdData        bool    `json:"cold_data"`
	DaysSinceAccess float64 `json:"days_since_access"`
}

type HotnessConfig struct {
	ColdThresholdDays   float64
	HotThresholdScore   float64
	DecayFactor         float64
	MaxRecordsPerNode   int
}

type HotnessAnalyzer struct {
	config      HotnessConfig
	accessLogs  map[string][]AccessRecord
	nodeStats   map[string]*NodeHotness
	mu          sync.RWMutex
	storage     *storage.MemoryStorage
}

func NewHotnessAnalyzer(config HotnessConfig, storage *storage.MemoryStorage) *HotnessAnalyzer {
	return &HotnessAnalyzer{
		config:     config,
		accessLogs: make(map[string][]AccessRecord),
		nodeStats:  make(map[string]*NodeHotness),
		storage:    storage,
	}
}

func (h *HotnessAnalyzer) RecordAccess(path string, accessType AccessType) {
	h.mu.Lock()
	defer h.mu.Unlock()

	record := AccessRecord{
		Timestamp: time.Now(),
		Type:      accessType,
		Path:      path,
	}

	if _, exists := h.accessLogs[path]; !exists {
		h.accessLogs[path] = make([]AccessRecord, 0, h.config.MaxRecordsPerNode)
	}

	h.accessLogs[path] = append(h.accessLogs[path], record)
	if len(h.accessLogs[path]) > h.config.MaxRecordsPerNode {
		h.accessLogs[path] = h.accessLogs[path][1:]
	}

	stats, exists := h.nodeStats[path]
	if !exists {
		stats = &NodeHotness{Path: path}
		h.nodeStats[path] = stats
	}

	switch accessType {
	case AccessRead:
		stats.ReadCount++
	case AccessWrite:
		stats.WriteCount++
	case AccessWatch:
		stats.WatchCount++
	}
	stats.TotalAccess++
	stats.LastAccessTime = record.Timestamp
}

func (h *HotnessAnalyzer) calculateHotnessScore(path string) float64 {
	records, exists := h.accessLogs[path]
	if !exists || len(records) == 0 {
		return 0
	}

	now := time.Now()
	var score float64

	for _, record := range records {
		daysSince := now.Sub(record.Timestamp).Hours() / 24
		weight := math.Exp(-h.config.DecayFactor * daysSince)

		switch record.Type {
		case AccessRead:
			score += 1.0 * weight
		case AccessWrite:
			score += 3.0 * weight
		case AccessWatch:
			score += 2.0 * weight
		}
	}

	return score
}

func (h *HotnessAnalyzer) Analyze() {
	h.mu.Lock()
	defer h.mu.Unlock()

	now := time.Now()

	for path, stats := range h.nodeStats {
		stats.HotnessScore = h.calculateHotnessScore(path)

		if !stats.LastAccessTime.IsZero() {
			stats.DaysSinceAccess = now.Sub(stats.LastAccessTime).Hours() / 24
			stats.ColdData = stats.DaysSinceAccess >= h.config.ColdThresholdDays
		} else {
			stats.ColdData = true
			stats.DaysSinceAccess = 999
		}
	}
}

func (h *HotnessAnalyzer) GetColdDataNodes(threshold float64) []NodeHotness {
	h.Analyze()

	h.mu.RLock()
	defer h.mu.RUnlock()

	if threshold <= 0 {
		threshold = h.config.ColdThresholdDays
	}

	result := make([]NodeHotness, 0)
	for _, stats := range h.nodeStats {
		if stats.DaysSinceAccess >= threshold {
			result = append(result, *stats)
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].DaysSinceAccess > result[j].DaysSinceAccess
	})

	return result
}

func (h *HotnessAnalyzer) GetHotNodes(limit int) []NodeHotness {
	h.Analyze()

	h.mu.RLock()
	defer h.mu.RUnlock()

	result := make([]NodeHotness, 0, len(h.nodeStats))
	for _, stats := range h.nodeStats {
		result = append(result, *stats)
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].HotnessScore > result[j].HotnessScore
	})

	if len(result) > limit {
		result = result[:limit]
	}

	return result
}

func (h *HotnessAnalyzer) GetNodeHotness(path string) (*NodeHotness, bool) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	stats, exists := h.nodeStats[path]
	if !exists {
		return nil, false
	}

	statsCopy := *stats
	statsCopy.HotnessScore = h.calculateHotnessScore(path)
	return &statsCopy, true
}

func (h *HotnessAnalyzer) GenerateMigrationSuggestions(snapshot *storage.Snapshot) []map[string]interface{} {
	if snapshot == nil {
		return nil
	}

	coldNodes := h.GetColdDataNodes(0)
	suggestions := []map[string]interface{}{}

	coldByPrefix := make(map[string][]NodeHotness)
	for _, node := range coldNodes {
		for prefix := range snapshot.PathStats {
			if len(node.Path) >= len(prefix) && node.Path[:len(prefix)] == prefix {
				coldByPrefix[prefix] = append(coldByPrefix[prefix], node)
				break
			}
		}
	}

	for prefix, nodes := range coldByPrefix {
		if len(nodes) >= 10 {
			pathStat, exists := snapshot.PathStats[prefix]
			if !exists {
				continue
			}

			var totalSize int64
			for _, node := range nodes {
				if n, ok := snapshot.Nodes[node.Path]; ok {
					totalSize += n.DataSize
				}
			}

			suggestions = append(suggestions, map[string]interface{}{
				"prefix":           prefix,
				"cold_node_count":  len(nodes),
				"total_data_size":  totalSize,
				"avg_cold_days":    calculateAvgColdDays(nodes),
				"suggested_action": "migrate_to_cold_storage",
				"recommendations": []string{
					"将冷数据迁移到Redis（带过期策略）",
					"归档到对象存储（S3/OSS）",
					"写入时序数据库（InfluxDB/Prometheus）",
					"定期批量导出到文件系统",
				},
			})
		}
	}

	sort.Slice(suggestions, func(i, j int) bool {
		return suggestions[i]["cold_node_count"].(int) > suggestions[j]["cold_node_count"].(int)
	})

	return suggestions
}

func calculateAvgColdDays(nodes []NodeHotness) float64 {
	if len(nodes) == 0 {
		return 0
	}
	var total float64
	for _, node := range nodes {
		total += node.DaysSinceAccess
	}
	return total / float64(len(nodes))
}

func (h *HotnessAnalyzer) GetHotnessStats() map[string]interface{} {
	h.Analyze()

	h.mu.RLock()
	defer h.mu.RUnlock()

	totalNodes := len(h.nodeStats)
	coldCount := 0
	hotCount := 0

	for _, stats := range h.nodeStats {
		if stats.ColdData {
			coldCount++
		}
		if stats.HotnessScore >= h.config.HotThresholdScore {
			hotCount++
		}
	}

	return map[string]interface{}{
		"total_tracked_nodes": totalNodes,
		"cold_node_count":     coldCount,
		"hot_node_count":      hotCount,
		"cold_threshold_days": h.config.ColdThresholdDays,
		"hot_threshold_score": h.config.HotThresholdScore,
	}
}

func (h *HotnessAnalyzer) StartAnalysisJob(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Printf("Hotness analysis job started, interval: %v", interval)

	for range ticker.C {
		h.Analyze()
	}
}

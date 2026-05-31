package heatanalysis

import (
	"log"
	"sort"
	"sync"
	"time"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/types"

	"github.com/go-zookeeper/zk"
)

type HeatAnalyzer struct {
	conn       *zk.Conn
	heatMap    map[string]*types.HeatRecord
	mu         sync.RWMutex
	thresholds HeatThresholds
}

type HeatThresholds struct {
	HotReadCount   int64
	WarmReadCount  int64
	ColdDays       int
	HotWriteCount  int64
	WarmWriteCount int64
}

type MigrationSuggestion struct {
	Path        string `json:"path"`
	HeatLevel   string `json:"heat_level"`
	Reason      string `json:"reason"`
	TargetStore string `json:"target_store"`
	DataSize    int64  `json:"data_size"`
	LastAccess  string `json:"last_access"`
}

func NewHeatAnalyzer(conn *zk.Conn) *HeatAnalyzer {
	return &HeatAnalyzer{
		conn:    conn,
		heatMap: make(map[string]*types.HeatRecord),
		thresholds: HeatThresholds{
			HotReadCount:   100,
			WarmReadCount:  20,
			ColdDays:       7,
			HotWriteCount:  50,
			WarmWriteCount: 10,
		},
	}
}

func (ha *HeatAnalyzer) RecordAccess(path string, accessType string) {
	ha.mu.Lock()
	defer ha.mu.Unlock()
	if _, exists := ha.heatMap[path]; !exists {
		ha.heatMap[path] = &types.HeatRecord{
			Path:       path,
			ReadCount:  0,
			WriteCount: 0,
			LastAccess: time.Now(),
			HeatLevel:  "warm",
		}
	}
	record := ha.heatMap[path]
	record.LastAccess = time.Now()
	switch accessType {
	case "read":
		record.ReadCount++
	case "write":
		record.WriteCount++
	}
}

func (ha *HeatAnalyzer) AnalyzeFromSnapshots(snapshots []*storage.Snapshot) {
	ha.mu.Lock()
	defer ha.mu.Unlock()
	for _, snap := range snapshots {
		for path, node := range snap.Nodes {
			if _, exists := ha.heatMap[path]; !exists {
				ha.heatMap[path] = &types.HeatRecord{
					Path:       path,
					ReadCount:  0,
					WriteCount: 0,
					LastAccess: node.LastModified,
					HeatLevel:  "warm",
				}
			}
			record := ha.heatMap[path]
			if node.LastModified.After(record.LastAccess) {
				record.LastAccess = node.LastModified
			}
			if node.DataSize > 0 {
				record.WriteCount++
			}
		}
	}
	ha.classifyHeatLevels()
}

func (ha *HeatAnalyzer) classifyHeatLevels() {
	now := time.Now()
	for _, record := range ha.heatMap {
		daysSinceAccess := now.Sub(record.LastAccess).Hours() / 24
		switch {
		case record.ReadCount >= ha.thresholds.HotReadCount ||
			record.WriteCount >= ha.thresholds.HotWriteCount:
			record.HeatLevel = "hot"
		case record.ReadCount >= ha.thresholds.WarmReadCount ||
			record.WriteCount >= ha.thresholds.WarmWriteCount:
			if daysSinceAccess < 3 {
				record.HeatLevel = "hot"
			} else {
				record.HeatLevel = "warm"
			}
		case daysSinceAccess > float64(ha.thresholds.ColdDays):
			record.HeatLevel = "cold"
		case daysSinceAccess > float64(ha.thresholds.ColdDays)/2:
			record.HeatLevel = "warm"
		default:
			record.HeatLevel = "warm"
		}
	}
}

func (ha *HeatAnalyzer) scanAccessPatterns() {
	ha.mu.Lock()
	defer ha.mu.Unlock()

	stack := []string{"/"}
	visited := make(map[string]bool)

	for len(stack) > 0 {
		nodePath := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if visited[nodePath] {
			continue
		}
		visited[nodePath] = true

		_, stat, err := ha.conn.Exists(nodePath)
		if err != nil || stat == nil {
			continue
		}

		modTime := time.Unix(0, stat.Mtime*int64(time.Millisecond))
		ctime := time.Unix(0, stat.Ctime*int64(time.Millisecond))

		if _, exists := ha.heatMap[nodePath]; !exists {
			ha.heatMap[nodePath] = &types.HeatRecord{
				Path:       nodePath,
				ReadCount:  0,
				WriteCount: 1,
				LastAccess: modTime,
				HeatLevel:  "warm",
			}
		} else {
			record := ha.heatMap[nodePath]
			if modTime.After(record.LastAccess) {
				record.LastAccess = modTime
			}
			if time.Since(ctime).Hours() > 0 {
				record.WriteCount = int64(stat.Version + stat.Cversion)
				record.ReadCount = int64(stat.NumChildren)
			}
		}

		children, _, err := ha.conn.Children(nodePath)
		if err != nil {
			continue
		}
		for i := len(children) - 1; i >= 0; i-- {
			child := children[i]
			childPath := nodePath
			if childPath == "/" {
				childPath = "/" + child
			} else {
				childPath = childPath + "/" + child
			}
			if !visited[childPath] {
				stack = append(stack, childPath)
			}
		}
	}
	ha.classifyHeatLevels()
}

func (ha *HeatAnalyzer) GetHeatMap() map[string]*types.HeatRecord {
	ha.mu.RLock()
	defer ha.mu.RUnlock()
	result := make(map[string]*types.HeatRecord, len(ha.heatMap))
	for k, v := range ha.heatMap {
		result[k] = v
	}
	return result
}

func (ha *HeatAnalyzer) GetHeatStats() map[string]interface{} {
	ha.mu.RLock()
	defer ha.mu.RUnlock()
	hot, warm, cold := 0, 0, 0
	for _, record := range ha.heatMap {
		switch record.HeatLevel {
		case "hot":
			hot++
		case "cold":
			cold++
		default:
			warm++
		}
	}
	return map[string]interface{}{
		"hot":   hot,
		"warm":  warm,
		"cold":  cold,
		"total": hot + warm + cold,
	}
}

func (ha *HeatAnalyzer) GetColdNodes(snapshot *storage.Snapshot) []MigrationSuggestion {
	ha.mu.RLock()
	defer ha.mu.RUnlock()
	suggestions := []MigrationSuggestion{}
	for path, record := range ha.heatMap {
		if record.HeatLevel != "cold" {
			continue
		}
		dataSize := int64(0)
		if snapshot != nil {
			if node, ok := snapshot.Nodes[path]; ok {
				dataSize = node.DataSize
			}
		}
		target := "Redis"
		if dataSize > 1024*1024 {
			target = "HBase/Cassandra"
		} else if dataSize > 1024*100 {
			target = "LevelDB/RocksDB"
		}
		suggestions = append(suggestions, MigrationSuggestion{
			Path:        path,
			HeatLevel:   "cold",
			Reason:      "节点超过7天未访问，建议迁移至外部存储",
			TargetStore: target,
			DataSize:    dataSize,
			LastAccess:  record.LastAccess.Format("2006-01-02 15:04:05"),
		})
	}
	sort.Slice(suggestions, func(i, j int) bool {
		return suggestions[i].DataSize > suggestions[j].DataSize
	})
	return suggestions
}

func (ha *HeatAnalyzer) GetTopHotNodes(limit int) []*types.HeatRecord {
	ha.mu.RLock()
	defer ha.mu.RUnlock()
	records := make([]*types.HeatRecord, 0, len(ha.heatMap))
	for _, r := range ha.heatMap {
		records = append(records, r)
	}
	sort.Slice(records, func(i, j int) bool {
		return (records[i].ReadCount+records[i].WriteCount) > (records[j].ReadCount+records[j].WriteCount)
	})
	if len(records) > limit {
		records = records[:limit]
	}
	return records
}

func (ha *HeatAnalyzer) StartAnalysisJob(interval time.Duration, storage *storage.MemoryStorage) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	log.Printf("Heat analyzer started with interval %v", interval)
	for range ticker.C {
		ha.scanAccessPatterns()
		snapshots := storage.GetSnapshots(24 * time.Hour)
		ha.AnalyzeFromSnapshots(snapshots)
		stats := ha.GetHeatStats()
		log.Printf("Heat analysis: hot=%v warm=%v cold=%v",
			stats["hot"], stats["warm"], stats["cold"])
	}
}

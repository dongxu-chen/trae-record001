package monitor

import (
	"context"
	"math"
	"sync"
	"time"

	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
	"go.uber.org/zap"
)

type LoadMonitor struct {
	client        *elasticsearch.Client
	cfg           *config.LoadAwareness
	logger        *zap.Logger
	nodeHistory   map[string][]elasticsearch.NodeOSStats
	previousStats map[string]*elasticsearch.NodeOSStats
	mu            sync.RWMutex
	historySize   int
}

func NewLoadMonitor(client *elasticsearch.Client, cfg *config.LoadAwareness, logger *zap.Logger) *LoadMonitor {
	historySize := cfg.HistorySize
	if historySize <= 0 {
		historySize = 10
	}

	return &LoadMonitor{
		client:        client,
		cfg:           cfg,
		logger:        logger,
		nodeHistory:   make(map[string][]elasticsearch.NodeOSStats),
		previousStats: make(map[string]*elasticsearch.NodeOSStats),
		historySize:   historySize,
	}
}

func (lm *LoadMonitor) Start(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	lm.logger.Info("Load monitor started", zap.Duration("interval", interval))

	for {
		select {
		case <-ctx.Done():
			lm.logger.Info("Load monitor stopped")
			return
		case <-ticker.C:
			lm.CollectStats(ctx)
		}
	}
}

func (lm *LoadMonitor) CollectStats(ctx context.Context) {
	if !lm.cfg.Enabled {
		return
	}

	stats, err := lm.client.GetNodesOSStats(ctx)
	if err != nil {
		lm.logger.Error("Failed to collect node OS stats", zap.Error(err))
		return
	}

	nodes, err := lm.client.GetNodes(ctx)
	if err != nil {
		lm.logger.Error("Failed to get nodes info", zap.Error(err))
		return
	}

	lm.mu.Lock()
	defer lm.mu.Unlock()

	nodeIDToName := make(map[string]string)
	for nodeID, node := range nodes {
		nodeIDToName[nodeID] = node.Name
	}

	for nodeID, stat := range stats {
		nodeName, ok := nodeIDToName[nodeID]
		if !ok {
			continue
		}

		if prev, ok := lm.previousStats[nodeID]; ok {
			timeDiff := float64(stat.Timestamp - prev.Timestamp)
			if timeDiff > 0 {
				stat.IO.ReadBytesPerSec = int64(float64(stat.IO.TotalReadBytes-prev.IO.TotalReadBytes) / timeDiff)
				stat.IO.WriteBytesPerSec = int64(float64(stat.IO.TotalWriteBytes-prev.IO.TotalWriteBytes) / timeDiff)
			}
		}
		lm.previousStats[nodeID] = stat

		if _, ok := lm.nodeHistory[nodeName]; !ok {
			lm.nodeHistory[nodeName] = make([]elasticsearch.NodeOSStats, 0, lm.historySize)
		}

		lm.nodeHistory[nodeName] = append(lm.nodeHistory[nodeName], *stat)
		if len(lm.nodeHistory[nodeName]) > lm.historySize {
			lm.nodeHistory[nodeName] = lm.nodeHistory[nodeName][1:]
		}
	}

	lm.logger.Debug("Collected node load stats", zap.Int("node_count", len(stats)))
}

func (lm *LoadMonitor) GetNodeLoadHistory(nodeName string) *elasticsearch.NodeLoadHistory {
	lm.mu.RLock()
	defer lm.mu.RUnlock()

	history, ok := lm.nodeHistory[nodeName]
	if !ok || len(history) == 0 {
		return &elasticsearch.NodeLoadHistory{
			NodeName:   nodeName,
			History:    []elasticsearch.NodeOSStats{},
			AvgLoad:    0,
			AvgIOWait:  0,
			AvgCPU:     0,
			IsHighLoad: false,
			LoadScore:  0,
		}
	}

	var (
		totalLoad   float64
		totalIOWait float64
		totalCPU    float64
	)

	for _, stat := range history {
		load := stat.CPU.LoadAverage
		if len(stat.LoadAvg) > 0 {
			load = stat.LoadAvg[0]
		}
		totalLoad += load
		totalIOWait += stat.IO.IOWaitPercent
		totalCPU += float64(stat.CPU.Percent)
	}

	count := float64(len(history))
	avgLoad := totalLoad / count
	avgIOWait := totalIOWait / count
	avgCPU := totalCPU / count

	loadScore := lm.calculateLoadScore(avgLoad, avgIOWait, avgCPU)
	isHighLoad := lm.isHighLoadNode(avgLoad, avgIOWait, avgCPU)

	return &elasticsearch.NodeLoadHistory{
		NodeName:   nodeName,
		History:    history,
		AvgLoad:    avgLoad,
		AvgIOWait:  avgIOWait,
		AvgCPU:     avgCPU,
		IsHighLoad: isHighLoad,
		LoadScore:  loadScore,
	}
}

func (lm *LoadMonitor) GetAllLoadHistory() map[string]*elasticsearch.NodeLoadHistory {
	lm.mu.RLock()
	defer lm.mu.RUnlock()

	result := make(map[string]*elasticsearch.NodeLoadHistory)
	for nodeName := range lm.nodeHistory {
		result[nodeName] = lm.GetNodeLoadHistory(nodeName)
	}

	return result
}

func (lm *LoadMonitor) calculateLoadScore(load, ioWait, cpu float64) float64 {
	loadNorm := math.Min(load/10.0, 1.0)
	ioWaitNorm := math.Min(ioWait/100.0, 1.0)
	cpuNorm := math.Min(cpu/100.0, 1.0)

	score := loadNorm*0.4 + ioWaitNorm*0.3 + cpuNorm*0.3
	return math.Round(score*100) / 100
}

func (lm *LoadMonitor) isHighLoadNode(load, ioWait, cpu float64) bool {
	if !lm.cfg.Enabled {
		return false
	}

	if lm.cfg.HighLoadThreshold > 0 && lm.calculateLoadScore(load, ioWait, cpu) >= lm.cfg.HighLoadThreshold {
		return true
	}

	if lm.cfg.IOWaitThreshold > 0 && ioWait >= lm.cfg.IOWaitThreshold {
		return true
	}

	if lm.cfg.CPULoadThreshold > 0 && cpu >= lm.cfg.CPULoadThreshold*100 {
		return true
	}

	return false
}

func (lm *LoadMonitor) IsNodeHighLoad(nodeName string) bool {
	history := lm.GetNodeLoadHistory(nodeName)
	return history.IsHighLoad
}

func (lm *LoadMonitor) GetBestTargetNode(candidates []string) string {
	if len(candidates) == 0 {
		return ""
	}

	var bestNode string
	minScore := math.MaxFloat64

	for _, nodeName := range candidates {
		if lm.cfg.AvoidHighLoadNodes && lm.IsNodeHighLoad(nodeName) {
			continue
		}

		history := lm.GetNodeLoadHistory(nodeName)
		if history.LoadScore < minScore {
			minScore = history.LoadScore
			bestNode = nodeName
		}
	}

	if bestNode == "" && len(candidates) > 0 {
		bestNode = candidates[0]
	}

	return bestNode
}

func (lm *LoadMonitor) FilterLowLoadNodes(nodeNames []string) []string {
	if !lm.cfg.Enabled || !lm.cfg.AvoidHighLoadNodes {
		return nodeNames
	}

	var result []string
	for _, name := range nodeNames {
		if !lm.IsNodeHighLoad(name) {
			result = append(result, name)
		}
	}

	if len(result) == 0 {
		return nodeNames
	}

	return result
}

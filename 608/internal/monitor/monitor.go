package monitor

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/pkg/config"
)

type MetricPoint struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

type NodeMetrics struct {
	NodeID       string  `json:"node_id"`
	Addr         string  `json:"addr"`
	UsedMemory   float64 `json:"used_memory"`
	TotalMemory  float64 `json:"total_memory"`
	MemoryPct    float64 `json:"memory_pct"`
	QPS          float64 `json:"qps"`
	HitRate      float64 `json:"hit_rate"`
	Keys         int64   `json:"keys"`
	Expires      int64   `json:"expires"`
	Connected    bool    `json:"connected"`
	Role         string  `json:"role"`
	SlotCount    int     `json:"slot_count"`
}

type ClusterMetrics struct {
	Timestamp    int64         `json:"timestamp"`
	Nodes        []NodeMetrics `json:"nodes"`
	TotalQPS     float64       `json:"total_qps"`
	AvgMemoryPct float64       `json:"avg_memory_pct"`
	AvgHitRate   float64       `json:"avg_hit_rate"`
	TotalKeys    int64         `json:"total_keys"`
	MasterCount  int           `json:"master_count"`
}

type Monitor struct {
	clusterMgr  *cluster.Manager
	clusterCfg  config.ClusterConfig
	history     []*ClusterMetrics
	historyMu   sync.RWMutex
	historySize int
	interval    time.Duration
	stopCh      chan struct{}
}

func New(clusterMgr *cluster.Manager, clusterCfg config.ClusterConfig, historySize int, interval time.Duration) *Monitor {
	return &Monitor{
		clusterMgr:  clusterMgr,
		clusterCfg:  clusterCfg,
		historySize: historySize,
		interval:    interval,
		stopCh:      make(chan struct{}),
	}
}

func (m *Monitor) Start(ctx context.Context) {
	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-m.stopCh:
			return
		case <-ticker.C:
			metrics, err := m.collect(ctx)
			if err != nil {
				continue
			}
			m.addHistory(metrics)
		}
	}
}

func (m *Monitor) Stop() {
	close(m.stopCh)
}

func (m *Monitor) collect(ctx context.Context) (*ClusterMetrics, error) {
	nodes, err := m.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, fmt.Errorf("get nodes: %w", err)
	}

	cm := &ClusterMetrics{
		Timestamp: time.Now().Unix(),
	}

	var totalQPS, totalMemPct, totalHitRate float64
	var masterCount int

	for _, node := range nodes {
		nm := NodeMetrics{
			NodeID:      node.ID,
			Addr:        node.Addr,
			UsedMemory:  float64(node.Memory.UsedBytes),
			TotalMemory: float64(node.Memory.TotalBytes),
			MemoryPct:   node.Memory.UsedPercent,
			Connected:   node.Connected,
			Role:        node.Role,
		}

		slotCount := 0
		for _, sr := range node.Slots {
			slotCount += int(sr.End-sr.Start) + 1
		}
		nm.SlotCount = slotCount

		keys, expires := parseKeyspace(node.Keyspace)
		nm.Keys = keys
		nm.Expires = expires

		qps, hitRate, sErr := m.getNodeStats(ctx, node.Addr)
		if sErr == nil {
			nm.QPS = qps
			nm.HitRate = hitRate
		}

		cm.Nodes = append(cm.Nodes, nm)
		cm.TotalKeys += keys

		if node.Role == "master" {
			masterCount++
			totalQPS += nm.QPS
			totalMemPct += nm.MemoryPct
			totalHitRate += nm.HitRate
		}
	}

	cm.MasterCount = masterCount
	cm.TotalQPS = totalQPS
	if masterCount > 0 {
		cm.AvgMemoryPct = totalMemPct / float64(masterCount)
		cm.AvgHitRate = totalHitRate / float64(masterCount)
	}

	return cm, nil
}

func (m *Monitor) getNodeStats(ctx context.Context, addr string) (qps float64, hitRate float64, err error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: m.clusterCfg.Password,
	})
	defer client.Close()

	result, infoErr := client.Info(ctx, "stats").Result()
	if infoErr != nil {
		return 0, 0, infoErr
	}

	stats := parseInfoResult(result)

	cmdInstant, ok := stats["instantaneous_ops_per_sec"]
	if ok {
		qps, _ = strconv.ParseFloat(cmdInstant, 64)
	}

	keyspaceHits, ok1 := stats["keyspace_hits"]
	keyspaceMisses, ok2 := stats["keyspace_misses"]
	if ok1 && ok2 {
		hits, _ := strconv.ParseFloat(keyspaceHits, 64)
		misses, _ := strconv.ParseFloat(keyspaceMisses, 64)
		total := hits + misses
		if total > 0 {
			hitRate = hits / total * 100
		}
	}

	return qps, hitRate, nil
}

func parseInfoResult(info string) map[string]string {
	result := make(map[string]string)
	for _, line := range strings.Split(info, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) == 2 {
			result[strings.TrimSpace(parts[0])] = strings.TrimSpace(parts[1])
		}
	}
	return result
}

func parseKeyspace(info string) (keys int64, expires int64) {
	for _, line := range strings.Split(info, "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "db") {
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			continue
		}
		for _, pair := range strings.Split(parts[1], ",") {
			kv := strings.SplitN(pair, "=", 2)
			if len(kv) != 2 {
				continue
			}
			switch kv[0] {
			case "keys":
				keys, _ = strconv.ParseInt(kv[1], 10, 64)
			case "expires":
				expires, _ = strconv.ParseInt(kv[1], 10, 64)
			}
		}
	}
	return
}

func (m *Monitor) addHistory(metrics *ClusterMetrics) {
	m.historyMu.Lock()
	defer m.historyMu.Unlock()

	m.history = append(m.history, metrics)
	if len(m.history) > m.historySize {
		m.history = m.history[len(m.history)-m.historySize:]
	}
}

func (m *Monitor) GetHistory() []*ClusterMetrics {
	m.historyMu.RLock()
	defer m.historyMu.RUnlock()

	result := make([]*ClusterMetrics, len(m.history))
	copy(result, m.history)
	return result
}

func (m *Monitor) GetLatest() *ClusterMetrics {
	m.historyMu.RLock()
	defer m.historyMu.RUnlock()

	if len(m.history) == 0 {
		return nil
	}
	return m.history[len(m.history)-1]
}

func (m *Monitor) GetTimeRange(from, to int64) []*ClusterMetrics {
	m.historyMu.RLock()
	defer m.historyMu.RUnlock()

	var result []*ClusterMetrics
	for _, metric := range m.history {
		if metric.Timestamp >= from && metric.Timestamp <= to {
			result = append(result, metric)
		}
	}
	return result
}

package failover

import (
	"context"
	"fmt"
	"log"
	"sort"
	"sync"
	"time"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/pkg/config"

	"github.com/go-redis/redis/v8"
)

type FailoverEvent struct {
	Timestamp     int64  `json:"timestamp"`
	MasterID      string `json:"old_master_id"`
	MasterAddr    string `json:"old_master_addr"`
	ReplicaID     string `json:"new_master_id"`
	ReplicaAddr   string `json:"new_master_addr"`
	Status        string `json:"status"`
	Error         string `json:"error,omitempty"`
	FailureReason string `json:"failure_reason,omitempty"`
	DurationMs    int64  `json:"duration_ms,omitempty"`
	Type          string `json:"type"`
	Details       string `json:"details,omitempty"`
}

type NodeHealth struct {
	NodeID              string    `json:"node_id"`
	Addr                string    `json:"address"`
	Role                string    `json:"role"`
	Connected           bool      `json:"connected"`
	LastCheck           time.Time `json:"last_check"`
	FailCount           int       `json:"consecutive_failures"`
	HealthScore         float64   `json:"health_score"`
	LatencyMs           int64     `json:"latency_ms"`
	IsFailed            bool      `json:"is_failed"`
	Status              string    `json:"status"`
}

type FailoverManager struct {
	cfg           config.FailoverConfig
	clusterCfg    config.ClusterConfig
	clusterMgr    *cluster.Manager
	nodeHealth    map[string]*NodeHealth
	nodeHealthMu  sync.RWMutex
	events        []FailoverEvent
	eventsMu      sync.RWMutex
	stopCh        chan struct{}
}

func New(cfg config.FailoverConfig, clusterCfg config.ClusterConfig, clusterMgr *cluster.Manager) *FailoverManager {
	return &FailoverManager{
		cfg:         cfg,
		clusterCfg:  clusterCfg,
		clusterMgr:  clusterMgr,
		nodeHealth:  make(map[string]*NodeHealth),
		events:      make([]FailoverEvent, 0),
		stopCh:      make(chan struct{}),
	}
}

func (f *FailoverManager) Start(ctx context.Context) {
	if !f.cfg.Enabled {
		log.Println("[Failover] Auto-failover disabled")
		return
	}

	interval := time.Duration(f.cfg.HealthCheckIntervalSec) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Printf("[Failover] Started with health check interval: %v, failure threshold: %d/%d",
		interval, f.cfg.FailureThreshold, f.cfg.HealthCheckRetries)

	for {
		select {
		case <-ctx.Done():
			return
		case <-f.stopCh:
			return
		case <-ticker.C:
			f.healthCheckLoop(ctx)
		}
	}
}

func (f *FailoverManager) Stop() {
	close(f.stopCh)
}

func (f *FailoverManager) healthCheckLoop(ctx context.Context) {
	nodes, err := f.clusterMgr.GetNodes(ctx)
	if err != nil {
		log.Printf("[Failover] Failed to get cluster nodes: %v", err)
		return
	}

	for _, node := range nodes {
		f.checkNodeHealth(ctx, &node)
	}

	for _, node := range nodes {
		if node.Role != "master" {
			continue
		}

		health := f.getHealth(node.ID)
		if health == nil {
			continue
		}

		if health.IsFailed && f.cfg.AutoFailover {
			log.Printf("[Failover] Master %s (%s) detected as failed, triggering failover...",
				node.ID[:8], node.Addr)
			go f.performFailover(ctx, node.ID, node.Addr)
		}
	}
}

func (f *FailoverManager) checkNodeHealth(ctx context.Context, node *cluster.NodeInfo) {
	start := time.Now()

	client := redis.NewClient(&redis.Options{
		Addr:         node.Addr,
		Password:     f.clusterCfg.Password,
		DialTimeout:  2 * time.Second,
		ReadTimeout:  2 * time.Second,
		WriteTimeout: 2 * time.Second,
	})
	defer client.Close()

	health := f.getOrCreateHealth(node.ID, node.Addr, node.Role)
	health.LastCheck = time.Now()

	err := client.Ping(ctx).Err()
	latency := time.Since(start).Milliseconds()
	health.LatencyMs = latency

	if err != nil {
		health.Connected = false
		health.FailCount++

		health.HealthScore = f.calculateHealthScore(health)

		if health.FailCount >= f.cfg.FailureThreshold {
			health.IsFailed = true
		}

		log.Printf("[Failover] Node %s (%s) health check failed (%d/%d): %v",
			node.ID[:8], node.Addr, health.FailCount, f.cfg.FailureThreshold, err)
	} else {
		health.Connected = true
		health.FailCount = 0
		health.IsFailed = false

		health.HealthScore = f.calculateHealthScore(health)
	}

	f.updateHealth(health)
}

func (f *FailoverManager) calculateHealthScore(health *NodeHealth) float64 {
	if !health.Connected {
		return 0
	}

	score := 100.0

	if health.FailCount > 0 {
		score -= float64(health.FailCount) * 20
	}

	if health.LatencyMs > 500 {
		score -= 20
	} else if health.LatencyMs > 200 {
		score -= 10
	}

	if score < 0 {
		score = 0
	}

	return score
}

func (f *FailoverManager) performFailover(ctx context.Context, masterID, masterAddr string) error {
	start := time.Now()

	nodes, err := f.clusterMgr.GetNodes(ctx)
	if err != nil {
		return fmt.Errorf("get nodes: %w", err)
	}

	var replicas []cluster.NodeInfo
	for _, node := range nodes {
		if node.Role == "replica" && node.MasterID == masterID {
			replicas = append(replicas, node)
		}
	}

	if len(replicas) == 0 {
		event := FailoverEvent{
			Timestamp:     time.Now().Unix(),
			MasterID:      masterID,
			MasterAddr:    masterAddr,
			Status:        "failed",
			FailureReason: "no_replica_available",
			Error:         "no replicas found for failed master",
			Type:          "auto",
			Details:       "没有可用的从节点进行故障转移",
		}
		f.addEvent(event)
		return fmt.Errorf("no replicas available for master %s", masterID)
	}

	bestReplica := f.selectBestReplica(replicas)
	log.Printf("[Failover] Selected best replica %s (%s) for promotion",
		bestReplica.ID[:8], bestReplica.Addr)

	event := FailoverEvent{
		Timestamp:   time.Now().Unix(),
		MasterID:    masterID,
		MasterAddr:  masterAddr,
		ReplicaID:   bestReplica.ID,
		ReplicaAddr: bestReplica.Addr,
		Status:      "in_progress",
		Type:        "auto",
		Details:     fmt.Sprintf("自动故障转移：%s -> %s", masterAddr, bestReplica.Addr),
	}
	f.addEvent(event)

	replicaClient := redis.NewClient(&redis.Options{
		Addr:     bestReplica.Addr,
		Password: f.clusterCfg.Password,
	})
	defer replicaClient.Close()

	clusterFailoverCmd := replicaClient.ClusterFailover(ctx, true)
	if clusterFailoverCmd.Err() != nil {
		event.Status = "failed"
		event.Error = clusterFailoverCmd.Err().Error()
		event.DurationMs = time.Since(start).Milliseconds()
		event.Details = fmt.Sprintf("故障转移失败：%v", clusterFailoverCmd.Err())
		f.addEvent(event)
		return fmt.Errorf("cluster failover: %w", clusterFailoverCmd.Err())
	}

	time.Sleep(5 * time.Second)

	success := f.verifyPromotion(ctx, bestReplica.ID)
	if !success {
		event.Status = "verification_failed"
		event.Error = "replica promotion verification failed"
		event.DurationMs = time.Since(start).Milliseconds()
		event.Details = "从节点晋升验证失败"
		f.addEvent(event)
		return fmt.Errorf("failed to verify replica promotion")
	}

	event.Status = "success"
	event.DurationMs = time.Since(start).Milliseconds()
	event.Details = fmt.Sprintf("故障转移成功，耗时 %dms", event.DurationMs)
	f.addEvent(event)

	log.Printf("[Failover] Failover completed successfully in %dms: %s -> %s",
		event.DurationMs, masterAddr, bestReplica.Addr)

	f.resetHealth(masterID)

	return nil
}

func (f *FailoverManager) selectBestReplica(replicas []cluster.NodeInfo) cluster.NodeInfo {
	type scoredReplica struct {
		node  cluster.NodeInfo
		score float64
	}

	scored := make([]scoredReplica, 0, len(replicas))
	for _, repl := range replicas {
		score := 0.0

		health := f.getHealth(repl.ID)
		if health != nil {
			score += health.HealthScore

			if health.Connected {
				score += 50
			}

			if health.LatencyMs < 50 {
				score += 30
			} else if health.LatencyMs < 100 {
				score += 20
			} else if health.LatencyMs < 200 {
				score += 10
			}
		}

		if repl.Connected {
			score += 30
		}

		if repl.Memory.PeakBytes > 0 {
			memPct := repl.Memory.UsedPercent
			if memPct < 50 {
				score += 20
			} else if memPct < 70 {
				score += 10
			}
		}

		scored = append(scored, scoredReplica{node: repl, score: score})
	}

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})

	return scored[0].node
}

func (f *FailoverManager) verifyPromotion(ctx context.Context, replicaID string) bool {
	nodes, err := f.clusterMgr.GetNodes(ctx)
	if err != nil {
		return false
	}

	for _, node := range nodes {
		if node.ID == replicaID && node.Role == "master" && node.Connected {
			return true
		}
	}

	return false
}

func (f *FailoverManager) TriggerManualFailover(ctx context.Context, masterID string) (*FailoverEvent, error) {
	nodes, err := f.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, fmt.Errorf("get nodes: %w", err)
	}

	var master *cluster.NodeInfo
	for i := range nodes {
		if nodes[i].ID == masterID && nodes[i].Role == "master" {
			master = &nodes[i]
			break
		}
	}

	if master == nil {
		return nil, fmt.Errorf("master %s not found", masterID)
	}

	err = f.performFailover(ctx, master.ID, master.Addr)
	if err != nil {
		return nil, err
	}

	events := f.GetEvents()
	if len(events) > 0 {
		lastEvent := events[len(events)-1]
		lastEvent.Type = "manual"
		lastEvent.Details = fmt.Sprintf("手动故障转移：%s -> %s", master.Addr, lastEvent.ReplicaAddr)
		return &lastEvent, nil
	}

	return nil, fmt.Errorf("failover triggered but no event recorded")
}

func (f *FailoverManager) getHealth(nodeID string) *NodeHealth {
	f.nodeHealthMu.RLock()
	defer f.nodeHealthMu.RUnlock()

	if h, ok := f.nodeHealth[nodeID]; ok {
		return h
	}
	return nil
}

func (f *FailoverManager) getOrCreateHealth(nodeID, addr, role string) *NodeHealth {
	f.nodeHealthMu.Lock()
	defer f.nodeHealthMu.Unlock()

	if h, ok := f.nodeHealth[nodeID]; ok {
		return h
	}

	h := &NodeHealth{
		NodeID:    nodeID,
		Addr:      addr,
		Role:      role,
		Connected: true,
		HealthScore: 100,
	}
	f.nodeHealth[nodeID] = h
	return h
}

func (f *FailoverManager) updateHealth(health *NodeHealth) {
	f.nodeHealthMu.Lock()
	defer f.nodeHealthMu.Unlock()
	f.nodeHealth[health.NodeID] = health
}

func (f *FailoverManager) resetHealth(nodeID string) {
	f.nodeHealthMu.Lock()
	defer f.nodeHealthMu.Unlock()

	if h, ok := f.nodeHealth[nodeID]; ok {
		h.FailCount = 0
		h.IsFailed = false
		h.HealthScore = 100
	}
}

func (f *FailoverManager) GetAllHealth() []NodeHealth {
	f.nodeHealthMu.RLock()
	defer f.nodeHealthMu.RUnlock()

	result := make([]NodeHealth, 0, len(f.nodeHealth))
	for _, h := range f.nodeHealth {
		nh := *h
		if nh.IsFailed {
			nh.Status = "failed"
		} else if !nh.Connected || nh.FailCount > 0 {
			nh.Status = "unhealthy"
		} else {
			nh.Status = "healthy"
		}
		result = append(result, nh)
	}
	return result
}

func (f *FailoverManager) addEvent(event FailoverEvent) {
	f.eventsMu.Lock()
	defer f.eventsMu.Unlock()

	f.events = append(f.events, event)
	if len(f.events) > 100 {
		f.events = f.events[len(f.events)-100:]
	}
}

func (f *FailoverManager) GetEvents() []FailoverEvent {
	f.eventsMu.RLock()
	defer f.eventsMu.RUnlock()

	result := make([]FailoverEvent, len(f.events))
	copy(result, f.events)
	return result
}

package scaler

import (
	"context"
	"log"
	"sync"
	"time"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/internal/migration"
	"redis-cluster-scaler/internal/monitor"
	"redis-cluster-scaler/pkg/config"
)

type ScalingAction string

const (
	ScaleUp   ScalingAction = "scale_up"
	ScaleDown ScalingAction = "scale_down"
	NoAction  ScalingAction = "no_action"
)

type ScalingEvent struct {
	Timestamp int64         `json:"timestamp"`
	Action    ScalingAction `json:"action"`
	Reason    string        `json:"reason"`
	NodeAddr  string        `json:"node_addr,omitempty"`
	NodeID    string        `json:"node_id,omitempty"`
	Status    string        `json:"status"`
}

type Scaler struct {
	cfg         config.ScalerConfig
	clusterCfg  config.ClusterConfig
	clusterMgr  *cluster.Manager
	monitor     *monitor.Monitor
	migrator    *migration.Migrator
	events      []ScalingEvent
	eventsMu    sync.RWMutex
	lastAction  time.Time
	stopCh      chan struct{}
}

func New(
	cfg config.ScalerConfig,
	clusterCfg config.ClusterConfig,
	clusterMgr *cluster.Manager,
	mon *monitor.Monitor,
	migrator *migration.Migrator,
) *Scaler {
	return &Scaler{
		cfg:        cfg,
		clusterCfg: clusterCfg,
		clusterMgr: clusterMgr,
		monitor:    mon,
		migrator:   migrator,
		events:     make([]ScalingEvent, 0),
		stopCh:     make(chan struct{}),
	}
}

func (s *Scaler) Start(ctx context.Context) {
	if !s.cfg.Enabled {
		log.Println("[Scaler] Auto-scaling disabled")
		return
	}

	interval := time.Duration(s.cfg.CheckIntervalSec) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Printf("[Scaler] Started with check interval: %v", interval)

	for {
		select {
		case <-ctx.Done():
			return
		case <-s.stopCh:
			return
		case <-ticker.C:
			s.evaluate(ctx)
		}
	}
}

func (s *Scaler) Stop() {
	close(s.stopCh)
}

func (s *Scaler) evaluate(ctx context.Context) {
	if time.Since(s.lastAction) < time.Duration(s.cfg.CooldownSec)*time.Second {
		return
	}

	latest := s.monitor.GetLatest()
	if latest == nil {
		return
	}

	stats, err := s.clusterMgr.GetClusterStats(ctx)
	if err != nil {
		return
	}

	avgMemPct := latest.AvgMemoryPct
	totalQPS := latest.TotalQPS
	avgHitRate := latest.AvgHitRate
	masterCount := stats.MasterCount

	var scaleUpReasons []string
	var scaleDownReasons []string

	if avgMemPct > s.cfg.MemoryThresholdUp*100 {
		scaleUpReasons = append(scaleUpReasons, "memory usage above threshold")
	}
	if totalQPS > s.cfg.QPSThresholdUp {
		scaleUpReasons = append(scaleUpReasons, "QPS above threshold")
	}
	if avgHitRate < s.cfg.HitRateThreshold*100 && avgHitRate > 0 {
		scaleUpReasons = append(scaleUpReasons, "hit rate below threshold")
	}

	if avgMemPct < s.cfg.MemoryThresholdDown*100 {
		scaleDownReasons = append(scaleDownReasons, "memory usage below threshold")
	}
	if totalQPS < s.cfg.QPSThresholdDown {
		scaleDownReasons = append(scaleDownReasons, "QPS below threshold")
	}

	if len(scaleUpReasons) > 0 && masterCount < s.cfg.MaxNodes {
		log.Printf("[Scaler] Scale up triggered: %v", scaleUpReasons)
		s.performScaleUp(ctx, scaleUpReasons)
		return
	}

	if len(scaleDownReasons) > 0 && masterCount > s.cfg.MinNodes {
		log.Printf("[Scaler] Scale down triggered: %v", scaleDownReasons)
		s.performScaleDown(ctx, scaleDownReasons)
	}
}

func (s *Scaler) performScaleUp(ctx context.Context, reasons []string) {
	event := ScalingEvent{
		Timestamp: time.Now().Unix(),
		Action:    ScaleUp,
		Reason:    joinReasons(reasons),
		Status:    "initiated",
	}
	s.addEvent(event)

	log.Println("[Scaler] Scale-up: please add a new Redis node and provide its address via the API")
	event.Status = "waiting_for_node"
	s.addEvent(event)
}

func (s *Scaler) performScaleDown(ctx context.Context, reasons []string) {
	nodes, err := s.clusterMgr.GetNodes(ctx)
	if err != nil {
		return
	}

	var targetNode *cluster.NodeInfo
	minSlots := 16384 + 1

	for i := range nodes {
		node := &nodes[i]
		if node.Role != "master" {
			continue
		}
		slotCount := 0
		for _, sr := range node.Slots {
			slotCount += int(sr.End-sr.Start) + 1
		}
		if slotCount < minSlots {
			minSlots = slotCount
			targetNode = node
		}
	}

	if targetNode == nil {
		return
	}

	event := ScalingEvent{
		Timestamp: time.Now().Unix(),
		Action:    ScaleDown,
		Reason:    joinReasons(reasons),
		NodeID:    targetNode.ID,
		NodeAddr:  targetNode.Addr,
		Status:    "migrating_slots",
	}
	s.addEvent(event)

	err = s.migrator.EvacuateNode(ctx, targetNode.ID)
	if err != nil {
		event.Status = "failed"
		s.addEvent(event)
		log.Printf("[Scaler] Failed to evacuate node %s: %v", targetNode.ID, err)
		return
	}

	err = s.clusterMgr.RemoveNode(ctx, targetNode.ID)
	if err != nil {
		event.Status = "failed"
		s.addEvent(event)
		log.Printf("[Scaler] Failed to remove node %s: %v", targetNode.ID, err)
		return
	}

	event.Status = "completed"
	s.addEvent(event)
	s.lastAction = time.Now()
	log.Printf("[Scaler] Successfully scaled down, removed node %s", targetNode.ID)
}

func (s *Scaler) AddNewNode(ctx context.Context, addr string) error {
	err := s.clusterMgr.AddNode(ctx, addr)
	if err != nil {
		return err
	}

	plan, err := s.migrator.RebalancePlan(ctx)
	if err != nil {
		return err
	}

	err = s.migrator.ExecutePlan(ctx, plan)
	if err != nil {
		return err
	}

	event := ScalingEvent{
		Timestamp: time.Now().Unix(),
		Action:    ScaleUp,
		Reason:    "manual scale up",
		NodeAddr:  addr,
		Status:    "completed",
	}
	s.addEvent(event)
	s.lastAction = time.Now()

	return nil
}

func (s *Scaler) RemoveNodeByID(ctx context.Context, nodeID string) error {
	err := s.migrator.EvacuateNode(ctx, nodeID)
	if err != nil {
		return err
	}

	err = s.clusterMgr.RemoveNode(ctx, nodeID)
	if err != nil {
		return err
	}

	event := ScalingEvent{
		Timestamp: time.Now().Unix(),
		Action:    ScaleDown,
		Reason:    "manual scale down",
		NodeID:    nodeID,
		Status:    "completed",
	}
	s.addEvent(event)
	s.lastAction = time.Now()

	return nil
}

func (s *Scaler) GetEvents() []ScalingEvent {
	s.eventsMu.RLock()
	defer s.eventsMu.RUnlock()

	result := make([]ScalingEvent, len(s.events))
	copy(result, s.events)
	return result
}

func (s *Scaler) addEvent(event ScalingEvent) {
	s.eventsMu.Lock()
	defer s.eventsMu.Unlock()

	s.events = append(s.events, event)
	if len(s.events) > 100 {
		s.events = s.events[len(s.events)-100:]
	}
}

func joinReasons(reasons []string) string {
	result := ""
	for i, r := range reasons {
		if i > 0 {
			result += "; "
		}
		result += r
	}
	return result
}

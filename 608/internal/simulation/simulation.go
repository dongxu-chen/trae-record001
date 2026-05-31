package simulation

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/internal/cost"
	"redis-cluster-scaler/pkg/config"
)

type SimulationType string

const (
	SimScaleUp     SimulationType = "scale_up"
	SimScaleDown   SimulationType = "scale_down"
	SimRebalance   SimulationType = "rebalance"
	SimFailover    SimulationType = "failover"
	SimAddReplica  SimulationType = "add_replica"
)

type ImpactAssessment struct {
	Category string  `json:"category"`
	Score    float64 `json:"score"`
	Details  string  `json:"details"`
	Severity string  `json:"severity"`
}

type SimulationResult struct {
	ID                string             `json:"id"`
	Type              SimulationType     `json:"type"`
	Description       string             `json:"description"`
	Timestamp         int64              `json:"timestamp"`
	Status            string             `json:"status"`
	DurationMs        int64              `json:"duration_ms,omitempty"`
	OriginalState     *ClusterState      `json:"original_state"`
	SimulatedState    *ClusterState      `json:"simulated_state"`
	Impacts           []ImpactAssessment `json:"impacts"`
	OverallScore      float64            `json:"overall_score"`
	RiskLevel         string             `json:"risk_level"`
	Recommendations   []string           `json:"recommendations"`
	CostImpact        *cost.ScalePrediction `json:"cost_impact,omitempty"`
	SlotMigrationPlan []SlotMigration    `json:"slot_migration_plan,omitempty"`
	Warnings          []string           `json:"warnings,omitempty"`
}

type ClusterState struct {
	MasterCount  int          `json:"master_count"`
	ReplicaCount int          `json:"replica_count"`
	TotalNodes   int          `json:"total_nodes"`
	TotalSlots   int          `json:"total_slots"`
	TotalKeys    int64        `json:"total_keys"`
	AvgMemoryPct float64      `json:"avg_memory_pct"`
	TotalMemory  int64        `json:"total_memory"`
	SlotBalance  float64      `json:"slot_balance"`
	Nodes        []NodeState  `json:"nodes"`
}

type NodeState struct {
	NodeID    string  `json:"node_id"`
	Addr      string  `json:"addr"`
	Role      string  `json:"role"`
	SlotCount int     `json:"slot_count"`
	MemoryPct float64 `json:"memory_pct"`
	QPS       float64 `json:"qps"`
	Keys      int64   `json:"keys"`
}

type SlotMigration struct {
	Slot    uint16 `json:"slot"`
	From    string `json:"from"`
	To      string `json:"to"`
	KeyCount int64 `json:"key_count"`
	EstimatedTimeMs int64 `json:"estimated_time_ms"`
}

type SimulationManager struct {
	cfg        config.SimulationConfig
	clusterMgr *cluster.Manager
	costMgr    *cost.CostManager
	results    []SimulationResult
}

func New(cfg config.SimulationConfig, clusterMgr *cluster.Manager, costMgr *cost.CostManager) *SimulationManager {
	return &SimulationManager{
		cfg:        cfg,
		clusterMgr: clusterMgr,
		costMgr:    costMgr,
		results:    make([]SimulationResult, 0),
	}
}

func (s *SimulationManager) SimulateScaleUp(ctx context.Context, addNodes int) (*SimulationResult, error) {
	start := time.Now()

	result := &SimulationResult{
		ID:          fmt.Sprintf("sim-scaleup-%d", time.Now().Unix()),
		Type:        SimScaleUp,
		Description: fmt.Sprintf("模拟扩容 %d 个主节点", addNodes),
		Timestamp:   time.Now().Unix(),
		Status:      "running",
	}

	originalState, err := s.captureState(ctx)
	if err != nil {
		return nil, fmt.Errorf("capture state: %w", err)
	}
	result.OriginalState = originalState

	if originalState.MasterCount+addNodes > s.cfg.MaxSimulatedNodes {
		result.Status = "failed"
		result.Warnings = append(result.Warnings,
			fmt.Sprintf("模拟节点数 %d 超过最大限制 %d", originalState.MasterCount+addNodes, s.cfg.MaxSimulatedNodes))
		return result, fmt.Errorf("max simulated nodes exceeded")
	}

	simulatedState := s.simulateScaleUpState(originalState, addNodes)
	result.SimulatedState = simulatedState

	slotMigrations := s.simulateSlotMigration(originalState, simulatedState)
	result.SlotMigrationPlan = slotMigrations

	costImpact, err := s.costMgr.PredictScaleUp(ctx, addNodes)
	if err == nil {
		result.CostImpact = costImpact
	}

	result.Impacts = s.assessImpacts(originalState, simulatedState, slotMigrations, string(SimScaleUp))
	result.OverallScore = s.calculateOverallScore(result.Impacts)
	result.RiskLevel = s.assessRisk(result.OverallScore, slotMigrations)
	result.Recommendations = s.generateRecommendations(result)

	result.Status = "completed"
	result.DurationMs = time.Since(start).Milliseconds()

	s.addResult(*result)

	return result, nil
}

func (s *SimulationManager) SimulateScaleDown(ctx context.Context, removeNodes int) (*SimulationResult, error) {
	start := time.Now()

	result := &SimulationResult{
		ID:          fmt.Sprintf("sim-scaledown-%d", time.Now().Unix()),
		Type:        SimScaleDown,
		Description: fmt.Sprintf("模拟缩容 %d 个主节点", removeNodes),
		Timestamp:   time.Now().Unix(),
		Status:      "running",
	}

	originalState, err := s.captureState(ctx)
	if err != nil {
		return nil, fmt.Errorf("capture state: %w", err)
	}
	result.OriginalState = originalState

	if originalState.MasterCount-removeNodes < 3 {
		result.Status = "failed"
		result.Warnings = append(result.Warnings, "缩容后节点数将低于 3 个，违反集群最小要求")
		result.Recommendations = append(result.Recommendations, "至少需要 3 个主节点以保证高可用性")
		return result, nil
	}

	simulatedState := s.simulateScaleDownState(originalState, removeNodes)
	result.SimulatedState = simulatedState

	slotMigrations := s.simulateSlotMigration(originalState, simulatedState)
	result.SlotMigrationPlan = slotMigrations

	costImpact, err := s.costMgr.PredictScaleDown(ctx, removeNodes)
	if err == nil {
		result.CostImpact = costImpact
	}

	result.Impacts = s.assessImpacts(originalState, simulatedState, slotMigrations, string(SimScaleDown))
	result.OverallScore = s.calculateOverallScore(result.Impacts)
	result.RiskLevel = s.assessRisk(result.OverallScore, slotMigrations)
	result.Recommendations = s.generateRecommendations(result)

	result.Status = "completed"
	result.DurationMs = time.Since(start).Milliseconds()

	s.addResult(*result)

	return result, nil
}

func (s *SimulationManager) SimulateRebalance(ctx context.Context) (*SimulationResult, error) {
	start := time.Now()

	result := &SimulationResult{
		ID:          fmt.Sprintf("sim-rebalance-%d", time.Now().Unix()),
		Type:        SimRebalance,
		Description: "模拟集群均衡",
		Timestamp:   time.Now().Unix(),
		Status:      "running",
	}

	originalState, err := s.captureState(ctx)
	if err != nil {
		return nil, fmt.Errorf("capture state: %w", err)
	}
	result.OriginalState = originalState

	simulatedState := s.simulateRebalanceState(originalState)
	result.SimulatedState = simulatedState

	slotMigrations := s.simulateSlotMigration(originalState, simulatedState)
	result.SlotMigrationPlan = slotMigrations

	costImpact, err := s.costMgr.PredictRebalance(ctx)
	if err == nil {
		result.CostImpact = costImpact
	}

	result.Impacts = s.assessImpacts(originalState, simulatedState, slotMigrations, string(SimRebalance))
	result.OverallScore = s.calculateOverallScore(result.Impacts)
	result.RiskLevel = s.assessRisk(result.OverallScore, slotMigrations)
	result.Recommendations = s.generateRecommendations(result)

	result.Status = "completed"
	result.DurationMs = time.Since(start).Milliseconds()

	s.addResult(*result)

	return result, nil
}

func (s *SimulationManager) SimulateFailover(ctx context.Context, masterID string) (*SimulationResult, error) {
	start := time.Now()

	result := &SimulationResult{
		ID:          fmt.Sprintf("sim-failover-%d", time.Now().Unix()),
		Type:        SimFailover,
		Description: fmt.Sprintf("模拟主节点 %s 故障转移", masterID[:8]),
		Timestamp:   time.Now().Unix(),
		Status:      "running",
	}

	originalState, err := s.captureState(ctx)
	if err != nil {
		return nil, fmt.Errorf("capture state: %w", err)
	}
	result.OriginalState = originalState

	found := false
	for _, n := range originalState.Nodes {
		if n.NodeID == masterID && n.Role == "master" {
			found = true
			break
		}
	}
	if !found {
		result.Status = "failed"
		result.Warnings = append(result.Warnings, fmt.Sprintf("主节点 %s 不存在", masterID))
		return result, nil
	}

	replicas := 0
	for _, n := range originalState.Nodes {
		if n.Role == "replica" && isReplicaOf(n.NodeID, masterID, originalState) {
			replicas++
		}
	}
	if replicas == 0 {
		result.Warnings = append(result.Warnings, "该主节点没有从节点，故障转移将失败")
	}

	simulatedState := s.simulateFailoverState(originalState, masterID)
	result.SimulatedState = simulatedState

	result.Impacts = s.assessFailoverImpacts(originalState, simulatedState, replicas)
	result.OverallScore = s.calculateOverallScore(result.Impacts)
	result.RiskLevel = s.assessRisk(result.OverallScore, nil)
	result.Recommendations = s.generateRecommendations(result)

	result.Status = "completed"
	result.DurationMs = time.Since(start).Milliseconds()

	s.addResult(*result)

	return result, nil
}

func (s *SimulationManager) captureState(ctx context.Context) (*ClusterState, error) {
	nodes, err := s.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, err
	}

	stats, err := s.clusterMgr.GetClusterStats(ctx)
	if err != nil {
		return nil, err
	}

	state := &ClusterState{
		TotalSlots:  16384,
	}

	var totalMemPct float64
	var masterCount int
	slotCounts := make([]int, 0)

	for _, node := range nodes {
		slotCount := 0
		for _, sr := range node.Slots {
			slotCount += int(sr.End - sr.Start + 1)
		}

		ns := NodeState{
			NodeID:    node.ID,
			Addr:      node.Addr,
			Role:      node.Role,
			SlotCount: slotCount,
			MemoryPct: node.Memory.UsedPercent,
			Keys:      countKeys(node.Keyspace),
		}

		state.Nodes = append(state.Nodes, ns)
		state.TotalKeys += ns.Keys
		state.TotalMemory += node.Memory.UsedBytes

		if node.Role == "master" {
			masterCount++
			totalMemPct += node.Memory.UsedPercent
			slotCounts = append(slotCounts, slotCount)
		}
	}

	state.MasterCount = masterCount
	state.ReplicaCount = len(nodes) - masterCount
	state.TotalNodes = len(nodes)

	if masterCount > 0 {
		state.AvgMemoryPct = totalMemPct / float64(masterCount)
		state.SlotBalance = calculateSlotBalance(slotCounts)
	}

	return state, nil
}

func (s *SimulationManager) simulateScaleUpState(orig *ClusterState, addNodes int) *ClusterState {
	sim := *orig
	sim.MasterCount += addNodes
	sim.TotalNodes += addNodes

	newAvgMemPct := orig.AvgMemoryPct * float64(orig.MasterCount) / float64(sim.MasterCount)
	sim.AvgMemoryPct = newAvgMemPct

	slotsPerNewMaster := 16384 / sim.MasterCount
	for i := 0; i < addNodes; i++ {
		nodeID := fmt.Sprintf("sim-new-%d", i)
		sim.Nodes = append(sim.Nodes, NodeState{
			NodeID:    nodeID,
			Addr:      fmt.Sprintf("sim-node-%d:6379", i),
			Role:      "master",
			SlotCount: slotsPerNewMaster,
			MemoryPct: 0,
		})
	}

	slotCounts := make([]int, 0)
	for _, n := range sim.Nodes {
		if n.Role == "master" {
			if n.SlotCount == 0 {
				n.SlotCount = slotsPerNewMaster
			}
			slotCounts = append(slotCounts, n.SlotCount)
		}
	}
	sim.SlotBalance = calculateSlotBalance(slotCounts)

	return &sim
}

func (s *SimulationManager) simulateScaleDownState(orig *ClusterState, removeNodes int) *ClusterState {
	sim := *orig
	sim.MasterCount -= removeNodes
	sim.TotalNodes -= removeNodes

	sort.Slice(sim.Nodes, func(i, j int) bool {
		return sim.Nodes[i].SlotCount < sim.Nodes[j].SlotCount
	})

	toRemove := removeNodes
	keptNodes := make([]NodeState, 0)
	for _, n := range sim.Nodes {
		if n.Role == "master" && toRemove > 0 {
			toRemove--
			continue
		}
		keptNodes = append(keptNodes, n)
	}
	sim.Nodes = keptNodes

	newSlotsPerMaster := 16384 / sim.MasterCount
	for i := range sim.Nodes {
		if sim.Nodes[i].Role == "master" {
			sim.Nodes[i].SlotCount = newSlotsPerMaster
		}
	}

	slotCounts := make([]int, 0)
	for _, n := range sim.Nodes {
		if n.Role == "master" {
			slotCounts = append(slotCounts, n.SlotCount)
		}
	}
	sim.SlotBalance = calculateSlotBalance(slotCounts)

	newAvgMemPct := orig.AvgMemoryPct * float64(orig.MasterCount) / float64(sim.MasterCount)
	sim.AvgMemoryPct = newAvgMemPct

	return &sim
}

func (s *SimulationManager) simulateRebalanceState(orig *ClusterState) *ClusterState {
	sim := *orig

	targetSlots := 16384 / sim.MasterCount
	remainder := 16384 % sim.MasterCount

	slotCounts := make([]int, 0)
	masterIdx := 0
	for i := range sim.Nodes {
		if sim.Nodes[i].Role == "master" {
			sim.Nodes[i].SlotCount = targetSlots
			if masterIdx < remainder {
				sim.Nodes[i].SlotCount++
			}
			slotCounts = append(slotCounts, sim.Nodes[i].SlotCount)
			masterIdx++
		}
	}

	sim.SlotBalance = calculateSlotBalance(slotCounts)

	return &sim
}

func (s *SimulationManager) simulateFailoverState(orig *ClusterState, masterID string) *ClusterState {
	sim := *orig

	for i := range sim.Nodes {
		if sim.Nodes[i].NodeID == masterID {
			sim.Nodes[i].Role = "failed"
			sim.Nodes[i].SlotCount = 0
		}
	}

	for i := range sim.Nodes {
		if sim.Nodes[i].Role == "replica" && isReplicaOf(sim.Nodes[i].NodeID, masterID, orig) {
			sim.Nodes[i].Role = "master"
			for j := range orig.Nodes {
				if orig.Nodes[j].NodeID == masterID {
					sim.Nodes[i].SlotCount = orig.Nodes[j].SlotCount
					sim.Nodes[i].MemoryPct = orig.Nodes[j].MemoryPct
					sim.Nodes[i].Keys = orig.Nodes[j].Keys
				}
			}
			break
		}
	}

	return &sim
}

func (s *SimulationManager) simulateSlotMigration(orig, sim *ClusterState) []SlotMigration {
	var migrations []SlotMigration

	origSlots := make(map[string]int)
	simSlots := make(map[string]int)
	origMasterIDs := make([]string, 0)

	for _, n := range orig.Nodes {
		if n.Role == "master" {
			origSlots[n.NodeID] = n.SlotCount
			origMasterIDs = append(origMasterIDs, n.NodeID)
		}
	}

	for _, n := range sim.Nodes {
		if n.Role == "master" {
			simSlots[n.NodeID] = n.SlotCount
		}
	}

	donors := make([]string, 0)
	recipients := make([]string, 0)
	diffMap := make(map[string]int)

	for _, id := range origMasterIDs {
		origCount := origSlots[id]
		simCount := simSlots[id]
		diff := simCount - origCount
		diffMap[id] = diff

		if diff < 0 {
			donors = append(donors, id)
		} else if diff > 0 {
			recipients = append(recipients, id)
		}
	}

	sort.Slice(donors, func(i, j int) bool {
		return diffMap[donors[i]] < diffMap[donors[j]]
	})
	sort.Slice(recipients, func(i, j int) bool {
		return diffMap[recipients[i]] > diffMap[recipients[j]]
	})

	slotCounter := uint16(0)
	avgKeysPerSlot := float64(orig.TotalKeys) / 16384.0
	timePerKey := int64(s.cfg.EstimatedMsPerKey)

	donorIdx := 0
	recipientIdx := 0

	for donorIdx < len(donors) && recipientIdx < len(recipients) {
		donorID := donors[donorIdx]
		recipientID := recipients[recipientIdx]

		donorGive := -diffMap[donorID]
		recipientNeed := diffMap[recipientID]

		toMove := min(donorGive, recipientNeed)

		for i := 0; i < toMove; i++ {
			migrations = append(migrations, SlotMigration{
				Slot:            slotCounter,
				From:            donorID,
				To:              recipientID,
				KeyCount:        int64(avgKeysPerSlot),
				EstimatedTimeMs: int64(avgKeysPerSlot) * timePerKey,
			})
			slotCounter++
		}

		diffMap[donorID] += toMove
		diffMap[recipientID] -= toMove

		if diffMap[donorID] == 0 {
			donorIdx++
		}
		if diffMap[recipientID] == 0 {
			recipientIdx++
		}
	}

	return migrations
}

func (s *SimulationManager) assessImpacts(orig, sim *ClusterState, migrations []SlotMigration, simType string) []ImpactAssessment {
	var impacts []ImpactAssessment

	memoryScore := 100.0
	if sim.AvgMemoryPct > orig.AvgMemoryPct && simType != "scale_down" {
		memoryScore = 100 - (sim.AvgMemoryPct - orig.AvgMemoryPct) * 5
	} else if sim.AvgMemoryPct < orig.AvgMemoryPct && simType != "scale_up" {
		memoryScore = 100 + (orig.AvgMemoryPct - sim.AvgMemoryPct) * 3
	}
	if memoryScore < 0 {
		memoryScore = 0
	}
	if memoryScore > 100 {
		memoryScore = 100
	}

	memorySeverity := "low"
	if memoryScore < 50 {
		memorySeverity = "high"
	} else if memoryScore < 80 {
		memorySeverity = "medium"
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "memory",
		Score:    memoryScore,
		Details:  fmt.Sprintf("平均内存使用率: %.1f%% → %.1f%%", orig.AvgMemoryPct, sim.AvgMemoryPct),
		Severity: memorySeverity,
	})

	slotBalanceScore := sim.SlotBalance
	slotBalanceSeverity := "low"
	if slotBalanceScore < 50 {
		slotBalanceSeverity = "high"
	} else if slotBalanceScore < 80 {
		slotBalanceSeverity = "medium"
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "slot_balance",
		Score:    slotBalanceScore,
		Details:  fmt.Sprintf("槽位均衡度: %.1f → %.1f", orig.SlotBalance, sim.SlotBalance),
		Severity: slotBalanceSeverity,
	})

	if len(migrations) > 0 {
		totalKeys := int64(0)
		totalTime := int64(0)
		for _, m := range migrations {
			totalKeys += m.KeyCount
			totalTime += m.EstimatedTimeMs
		}

		migrationScore := 100.0
		if len(migrations) > 1000 {
			migrationScore = 50.0
		} else if len(migrations) > 500 {
			migrationScore = 70.0
		}

		migrationSeverity := "low"
		if migrationScore < 50 {
			migrationSeverity = "high"
		} else if migrationScore < 80 {
			migrationSeverity = "medium"
		}

		impacts = append(impacts, ImpactAssessment{
			Category: "migration",
			Score:    migrationScore,
			Details:  fmt.Sprintf("需迁移 %d 个槽位, %d 个 key, 预计耗时 %d 秒",
				len(migrations), totalKeys, totalTime/1000),
			Severity: migrationSeverity,
		})
	}

	availabilityScore := 100.0
	if sim.MasterCount < 3 {
		availabilityScore = 0
	} else if sim.MasterCount < 5 {
		availabilityScore = 70
	}

	availabilitySeverity := "low"
	if availabilityScore < 50 {
		availabilitySeverity = "high"
	} else if availabilityScore < 80 {
		availabilitySeverity = "medium"
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "availability",
		Score:    availabilityScore,
		Details:  fmt.Sprintf("主节点数: %d → %d", orig.MasterCount, sim.MasterCount),
		Severity: availabilitySeverity,
	})

	replicationScore := 100.0
	if sim.ReplicaCount < sim.MasterCount {
		replicationScore = 70
	} else if sim.ReplicaCount == 0 {
		replicationScore = 0
	}

	replicationSeverity := "low"
	if replicationScore < 50 {
		replicationSeverity = "high"
	} else if replicationScore < 80 {
		replicationSeverity = "medium"
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "replication",
		Score:    replicationScore,
		Details:  fmt.Sprintf("从节点数: %d", sim.ReplicaCount),
		Severity: replicationSeverity,
	})

	return impacts
}

func (s *SimulationManager) assessFailoverImpacts(orig, sim *ClusterState, replicas int) []ImpactAssessment {
	var impacts []ImpactAssessment

	downtimeScore := 100.0
	if replicas == 0 {
		downtimeScore = 0
	} else if replicas < 2 {
		downtimeScore = 70
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "downtime",
		Score:    downtimeScore,
		Details:  fmt.Sprintf("可用从节点数: %d, 预计故障转移时间 10-30 秒", replicas),
		Severity: func() string {
			if downtimeScore < 50 {
				return "high"
			}
			return "low"
		}(),
	})

	dataLossScore := 100.0
	if replicas == 0 {
		dataLossScore = 0
	}

	impacts = append(impacts, ImpactAssessment{
		Category: "data_loss",
		Score:    dataLossScore,
		Details: func() string {
			if replicas == 0 {
				return "存在数据丢失风险，建议配置从节点"
			}
			return "从节点配置完整，无数据丢失风险"
		}(),
		Severity: func() string {
			if dataLossScore < 50 {
				return "high"
			}
			return "low"
		}(),
	})

	impacts = append(impacts, ImpactAssessment{
		Category: "availability",
		Score: func() float64 {
			if replicas > 0 {
				return 90.0
			}
			return 0.0
		}(),
		Details: func() string {
			if replicas > 0 {
				return "故障转移后服务可自动恢复"
			}
			return "无法自动恢复服务"
		}(),
		Severity: func() string {
			if replicas == 0 {
				return "high"
			}
			return "low"
		}(),
	})

	return impacts
}

func (s *SimulationManager) calculateOverallScore(impacts []ImpactAssessment) float64 {
	if len(impacts) == 0 {
		return 0
	}

	weights := map[string]float64{
		"memory":        0.25,
		"slot_balance":  0.20,
		"migration":     0.20,
		"availability":  0.25,
		"replication":   0.10,
		"downtime":      0.35,
		"data_loss":     0.35,
	}

	totalScore := 0.0
	totalWeight := 0.0

	for _, imp := range impacts {
		weight := weights[imp.Category]
		if weight == 0 {
			weight = 0.1
		}
		totalScore += imp.Score * weight
		totalWeight += weight
	}

	if totalWeight == 0 {
		return 0
	}

	return totalScore / totalWeight
}

func (s *SimulationManager) assessRisk(score float64, migrations []SlotMigration) string {
	migrationCount := len(migrations)

	if score < 50 {
		return "high"
	} else if score < 75 || migrationCount > 1000 {
		return "medium"
	}
	return "low"
}

func (s *SimulationManager) generateRecommendations(result *SimulationResult) []string {
	var recs []string

	if result.RiskLevel == "high" {
		recs = append(recs, "⚠️ 高风险操作，建议在维护窗口执行")
	}

	for _, imp := range result.Impacts {
		switch {
		case imp.Category == "availability" && imp.Severity == "high":
			recs = append(recs, "建议保持至少 3 个主节点以保证高可用性")
		case imp.Category == "memory" && imp.Severity == "high":
			recs = append(recs, "内存使用率过高，建议增加节点或清理数据")
		case imp.Category == "migration" && imp.Severity == "high":
			recs = append(recs, "迁移数据量较大，建议在低峰期执行")
		case imp.Category == "replication" && imp.Severity == "high":
			recs = append(recs, "建议为每个主节点配置至少 1 个从节点")
		case imp.Category == "data_loss" && imp.Severity == "high":
			recs = append(recs, "请在执行前创建完整备份")
		}
	}

	if result.CostImpact != nil {
		if result.CostImpact.MonthlyCostDiff > 0 {
			recs = append(recs,
				fmt.Sprintf("预计每月成本增加 ¥%.2f", result.CostImpact.MonthlyCostDiff))
		} else if result.CostImpact.MonthlyCostDiff < 0 {
			recs = append(recs,
				fmt.Sprintf("预计每月成本节省 ¥%.2f", -result.CostImpact.MonthlyCostDiff))
		}
	}

	if len(result.SlotMigrationPlan) > 100 {
		recs = append(recs, fmt.Sprintf("需迁移 %d 个槽位，建议分批执行", len(result.SlotMigrationPlan)))
	}

	if len(recs) == 0 {
		recs = append(recs, "✅ 模拟评估通过，可以安全执行")
	}

	return recs
}

func (s *SimulationManager) GetResults() []SimulationResult {
	return s.results
}

func (s *SimulationManager) addResult(result SimulationResult) {
	s.results = append(s.results, result)
	if len(s.results) > 50 {
		s.results = s.results[len(s.results)-50:]
	}
}

func calculateSlotBalance(slotCounts []int) float64 {
	if len(slotCounts) == 0 {
		return 0
	}

	total := 0
	for _, c := range slotCounts {
		total += c
	}
	avg := float64(total) / float64(len(slotCounts))
	if avg == 0 {
		return 100
	}

	variance := 0.0
	for _, c := range slotCounts {
		diff := float64(c) - avg
		variance += diff * diff
	}
	variance /= float64(len(slotCounts))

	stdDev := variance
	balance := 100.0 - (stdDev / avg * 100)
	if balance < 0 {
		balance = 0
	}

	return balance
}

func countKeys(keyspace string) int64 {
	var count int64
	for _, line := range strings.Split(keyspace, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "db") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				for _, pair := range strings.Split(parts[1], ",") {
					kv := strings.SplitN(pair, "=", 2)
					if len(kv) == 2 && kv[0] == "keys" {
						val, _ := strconv.ParseInt(kv[1], 10, 64)
						count += val
					}
				}
			}
		}
	}
	return count
}

func isReplicaOf(replicaID, masterID string, state *ClusterState) bool {
	for _, n := range state.Nodes {
		if n.NodeID == replicaID {
			return true
		}
	}
	return false
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

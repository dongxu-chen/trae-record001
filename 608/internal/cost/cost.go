package cost

import (
	"context"
	"fmt"
	"math"
	"time"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/pkg/config"
)

type NodeCost struct {
	NodeID         string  `json:"node_id"`
	Addr           string  `json:"addr"`
	Role           string  `json:"role"`
	HourlyCost     float64 `json:"hourly_cost"`
	DailyCost      float64 `json:"daily_cost"`
	MonthlyCost    float64 `json:"monthly_cost"`
	MemoryGB       float64 `json:"memory_gb"`
	PricePerGBHour float64 `json:"price_per_gb_hour"`
}

type CostSummary struct {
	CurrentNodes       int       `json:"current_nodes"`
	CurrentMasters     int       `json:"current_masters"`
	CurrentReplicas    int       `json:"current_replicas"`
	CurrentHourlyCost  float64   `json:"current_hourly_cost"`
	CurrentDailyCost   float64   `json:"current_daily_cost"`
	CurrentMonthlyCost float64   `json:"current_monthly_cost"`
	LastUpdated        int64     `json:"last_updated"`
	Currency           string    `json:"currency"`
	NodeCosts          []NodeCost `json:"node_costs"`
}

type ScalePrediction struct {
	Action            string  `json:"action"`
	Description       string  `json:"description"`
	TargetNodeCount   int     `json:"target_node_count"`
	NodeDiff          int     `json:"node_diff"`
	HourlyCostDiff    float64 `json:"hourly_cost_diff"`
	DailyCostDiff     float64 `json:"daily_cost_diff"`
	MonthlyCostDiff   float64 `json:"monthly_cost_diff"`
	NewHourlyCost     float64 `json:"new_hourly_cost"`
	NewDailyCost      float64 `json:"new_daily_cost"`
	NewMonthlyCost    float64 `json:"new_monthly_cost"`
	ExpectedMemoryPct float64 `json:"expected_memory_pct,omitempty"`
	ExpectedQPS       float64 `json:"expected_qps,omitempty"`
	ROI               float64 `json:"roi,omitempty"`
}

type CostManager struct {
	cfg        config.CostConfig
	clusterMgr *cluster.Manager
	currency   string
}

func New(cfg config.CostConfig, clusterMgr *cluster.Manager) *CostManager {
	return &CostManager{
		cfg:        cfg,
		clusterMgr: clusterMgr,
		currency:   "CNY",
	}
}

func (c *CostManager) GetCurrentCost(ctx context.Context) (*CostSummary, error) {
	nodes, err := c.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, fmt.Errorf("get nodes: %w", err)
	}

	summary := &CostSummary{
		LastUpdated: time.Now().Unix(),
		Currency:    c.currency,
	}

	for _, node := range nodes {
		if node.Role == "master" {
			summary.CurrentMasters++
		} else {
			summary.CurrentReplicas++
		}
		summary.CurrentNodes++

		memoryGB := float64(node.Memory.TotalBytes) / (1024 * 1024 * 1024)
		if memoryGB <= 0 {
			memoryGB = c.cfg.DefaultMemoryGB
		}

		pricePerGBHour := c.cfg.PricePerGBHour
		if pricePerGBHour <= 0 {
			pricePerGBHour = 0.15
		}

		hourlyCost := memoryGB * pricePerGBHour
		roleMultiplier := 1.0
		if node.Role == "master" {
			roleMultiplier = c.cfg.MasterMultiplier
		} else {
			roleMultiplier = c.cfg.ReplicaMultiplier
		}
		if roleMultiplier <= 0 {
			roleMultiplier = 1.0
		}

		hourlyCost *= roleMultiplier

		nodeCost := NodeCost{
			NodeID:         node.ID,
			Addr:           node.Addr,
			Role:           node.Role,
			MemoryGB:       memoryGB,
			PricePerGBHour: pricePerGBHour,
			HourlyCost:     hourlyCost,
			DailyCost:      hourlyCost * 24,
			MonthlyCost:    hourlyCost * 24 * 30,
		}

		summary.NodeCosts = append(summary.NodeCosts, nodeCost)
		summary.CurrentHourlyCost += hourlyCost
	}

	summary.CurrentDailyCost = summary.CurrentHourlyCost * 24
	summary.CurrentMonthlyCost = summary.CurrentHourlyCost * 24 * 30

	return summary, nil
}

func (c *CostManager) PredictScaleUp(ctx context.Context, addNodes int) (*ScalePrediction, error) {
	current, err := c.GetCurrentCost(ctx)
	if err != nil {
		return nil, err
	}

	if addNodes <= 0 {
		addNodes = 1
	}

	avgNodeCost := 0.0
	masterCount := 0
	for _, nc := range current.NodeCosts {
		if nc.Role == "master" {
			avgNodeCost += nc.HourlyCost
			masterCount++
		}
	}
	if masterCount > 0 {
		avgNodeCost /= float64(masterCount)
	} else {
		avgNodeCost = current.CurrentHourlyCost / float64(current.CurrentNodes)
	}

	newNodes := current.CurrentMasters + addNodes
	newHourlyCost := current.CurrentHourlyCost + avgNodeCost*float64(addNodes)

	expectedMemPct := 0.0
	if current.CurrentMasters > 0 {
		expectedMemPct = float64(current.CurrentMasters) / float64(newNodes) * 100
	}

	var metrics *cluster.ClusterStats
	stats, statsErr := c.clusterMgr.GetClusterStats(ctx)
	if statsErr == nil {
		metrics = stats
	}

	expectedQPS := 0.0
	if metrics != nil && current.CurrentMasters > 0 {
		expectedQPS = float64(newNodes) / float64(current.CurrentMasters) * 50000
	}

	roi := 0.0
	if newHourlyCost > 0 {
		roi = (expectedQPS / (newHourlyCost * 100)) / (50000 / (current.CurrentHourlyCost * 100))
	}

	return &ScalePrediction{
		Action:            "scale_up",
		Description:       fmt.Sprintf("增加 %d 个主节点", addNodes),
		TargetNodeCount:   newNodes,
		NodeDiff:          addNodes,
		HourlyCostDiff:    avgNodeCost * float64(addNodes),
		DailyCostDiff:     avgNodeCost * float64(addNodes) * 24,
		MonthlyCostDiff:   avgNodeCost * float64(addNodes) * 24 * 30,
		NewHourlyCost:     newHourlyCost,
		NewDailyCost:      newHourlyCost * 24,
		NewMonthlyCost:    newHourlyCost * 24 * 30,
		ExpectedMemoryPct: expectedMemPct,
		ExpectedQPS:       expectedQPS,
		ROI:               roi,
	}, nil
}

func (c *CostManager) PredictScaleDown(ctx context.Context, removeNodes int) (*ScalePrediction, error) {
	current, err := c.GetCurrentCost(ctx)
	if err != nil {
		return nil, err
	}

	if removeNodes <= 0 {
		removeNodes = 1
	}

	if current.CurrentMasters-removeNodes < 3 {
		return nil, fmt.Errorf("cannot scale down below minimum 3 master nodes")
	}

	var highestCost float64
	for _, nc := range current.NodeCosts {
		if nc.Role == "master" && nc.HourlyCost > highestCost {
			highestCost = nc.HourlyCost
		}
	}

	if highestCost == 0 && len(current.NodeCosts) > 0 {
		highestCost = current.CurrentHourlyCost / float64(current.CurrentNodes)
	}

	costReduction := highestCost * float64(removeNodes)
	newNodes := current.CurrentMasters - removeNodes
	newHourlyCost := current.CurrentHourlyCost - costReduction

	expectedMemPct := 0.0
	if current.CurrentMasters > 0 {
		expectedMemPct = float64(current.CurrentMasters) / float64(newNodes) * 100
	}

	return &ScalePrediction{
		Action:            "scale_down",
		Description:       fmt.Sprintf("移除 %d 个主节点", removeNodes),
		TargetNodeCount:   newNodes,
		NodeDiff:          -removeNodes,
		HourlyCostDiff:    -costReduction,
		DailyCostDiff:     -costReduction * 24,
		MonthlyCostDiff:   -costReduction * 24 * 30,
		NewHourlyCost:     newHourlyCost,
		NewDailyCost:      newHourlyCost * 24,
		NewMonthlyCost:    newHourlyCost * 24 * 30,
		ExpectedMemoryPct: expectedMemPct,
	}, nil
}

func (c *CostManager) PredictRebalance(ctx context.Context) (*ScalePrediction, error) {
	current, err := c.GetCurrentCost(ctx)
	if err != nil {
		return nil, err
	}

	nodes, err := c.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, err
	}

	var masters []NodeCost
	for _, nc := range current.NodeCosts {
		for _, node := range nodes {
			if node.ID == nc.NodeID && node.Role == "master" {
				masters = append(masters, nc)
			}
		}
	}

	if len(masters) == 0 {
		return nil, fmt.Errorf("no master nodes found")
	}

	maxCost := 0.0
	minCost := math.MaxFloat64
	for _, m := range masters {
		if m.HourlyCost > maxCost {
			maxCost = m.HourlyCost
		}
		if m.HourlyCost < minCost {
			minCost = m.HourlyCost
		}
	}

	imbalance := 0.0
	if maxCost > 0 {
		imbalance = (maxCost - minCost) / maxCost * 100
	}

	expectedSavings := current.CurrentHourlyCost * 0.05
	if imbalance > 20 {
		expectedSavings = current.CurrentHourlyCost * (imbalance / 200)
	}

	return &ScalePrediction{
		Action:          "rebalance",
		Description:     "集群负载均衡",
		TargetNodeCount: current.CurrentMasters,
		NodeDiff:        0,
		HourlyCostDiff:  -expectedSavings,
		DailyCostDiff:   -expectedSavings * 24,
		MonthlyCostDiff: -expectedSavings * 24 * 30,
		NewHourlyCost:   current.CurrentHourlyCost - expectedSavings,
		NewDailyCost:    (current.CurrentHourlyCost - expectedSavings) * 24,
		NewMonthlyCost:  (current.CurrentHourlyCost - expectedSavings) * 24 * 30,
		ROI:             imbalance,
	}, nil
}

func (c *CostManager) PredictAddReplica(ctx context.Context, addReplicas int) (*ScalePrediction, error) {
	current, err := c.GetCurrentCost(ctx)
	if err != nil {
		return nil, err
	}

	if addReplicas <= 0 {
		addReplicas = 1
	}

	avgReplicaCost := 0.0
	replicaCount := 0
	for _, nc := range current.NodeCosts {
		if nc.Role == "replica" {
			avgReplicaCost += nc.HourlyCost
			replicaCount++
		}
	}

	if replicaCount > 0 {
		avgReplicaCost /= float64(replicaCount)
	} else {
		avgReplicaCost = current.CurrentHourlyCost / float64(current.CurrentNodes) * c.cfg.ReplicaMultiplier / c.cfg.MasterMultiplier
	}

	hourlyDiff := avgReplicaCost * float64(addReplicas)
	newHourlyCost := current.CurrentHourlyCost + hourlyDiff

	return &ScalePrediction{
		Action:          "add_replica",
		Description:     fmt.Sprintf("增加 %d 个从节点", addReplicas),
		TargetNodeCount: current.CurrentReplicas + addReplicas,
		NodeDiff:        addReplicas,
		HourlyCostDiff:  hourlyDiff,
		DailyCostDiff:   hourlyDiff * 24,
		MonthlyCostDiff: hourlyDiff * 24 * 30,
		NewHourlyCost:   newHourlyCost,
		NewDailyCost:    newHourlyCost * 24,
		NewMonthlyCost:  newHourlyCost * 24 * 30,
	}, nil
}

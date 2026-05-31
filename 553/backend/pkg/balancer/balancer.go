package balancer

import (
	"context"
	"fmt"
	"math"
	"sort"
	"strconv"
	"time"

	"go.uber.org/zap"
	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
	"es-shard-balancer/pkg/monitor"
)

type Balancer struct {
	client           *elasticsearch.Client
	cfg              *config.BalancerConfig
	logger           *zap.Logger
	loadMonitor      *monitor.LoadMonitor
	speedCtrl        *monitor.SpeedController
	shardHeatMonitor *monitor.ShardHeatMonitor
}

func NewBalancer(client *elasticsearch.Client, cfg *config.BalancerConfig, logger *zap.Logger, loadMonitor *monitor.LoadMonitor, speedCtrl *monitor.SpeedController, shardHeatMonitor *monitor.ShardHeatMonitor) *Balancer {
	return &Balancer{
		client:           client,
		cfg:              cfg,
		logger:           logger,
		loadMonitor:      loadMonitor,
		speedCtrl:        speedCtrl,
		shardHeatMonitor: shardHeatMonitor,
	}
}

func (b *Balancer) calculateDynamicWatermark(node *elasticsearch.NodeShardInfo) (low, high, flood float64) {
	cfg := b.cfg.DiskWatermark

	if !cfg.DynamicEnabled {
		return cfg.Low, cfg.High, cfg.Flood
	}

	totalGB := float64(node.DiskUsage.TotalBytes) / (1024 * 1024 * 1024)
	baseGB := cfg.BaseCapacityGB
	if baseGB <= 0 {
		baseGB = 500
	}

	ratio := totalGB / baseGB
	maxExtra := cfg.MaxExtraPercent
	if maxExtra <= 0 {
		maxExtra = 10
	}

	extraPercent := math.Min((ratio-1)*2, maxExtra)
	if extraPercent < 0 {
		extraPercent = 0
	}

	low = cfg.Low + extraPercent
	high = cfg.High + extraPercent
	flood = cfg.Flood + extraPercent

	low = math.Min(low, 95)
	high = math.Min(high, 97)
	flood = math.Min(flood, 99)

	return low, high, flood
}

func (b *Balancer) AnalyzeDistribution(ctx context.Context) (*elasticsearch.ShardDistribution, error) {
	dist, err := b.client.GetShardDistribution(
		ctx,
		b.cfg.HotCold.Enabled,
		b.cfg.HotCold.HotNodeAttr,
		b.cfg.HotCold.HotNodeValue,
		b.cfg.HotCold.ColdNodeAttr,
		b.cfg.HotCold.ColdNodeValue,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to get shard distribution: %w", err)
	}

	return dist, nil
}

func (b *Balancer) GenerateMigrationPlan(ctx context.Context) ([]elasticsearch.MigrationPlan, error) {
	dist, err := b.AnalyzeDistribution(ctx)
	if err != nil {
		return nil, err
	}

	var plans []elasticsearch.MigrationPlan

	plans = append(plans, b.planForDiskWatermark(dist)...)
	plans = append(plans, b.planForHotCold(dist)...)
	plans = append(plans, b.planForBalance(dist)...)

	plans = b.populateHeatInfo(plans)
	plans = b.sortPlansByHeat(plans)

	if len(plans) > b.cfg.MaxMigrationsPerCycle {
		plans = plans[:b.cfg.MaxMigrationsPerCycle]
	}

	for i := range plans {
		plans[i].CreatedAt = time.Now()
	}

	return plans, nil
}

func (b *Balancer) populateHeatInfo(plans []elasticsearch.MigrationPlan) []elasticsearch.MigrationPlan {
	if b.shardHeatMonitor == nil {
		return plans
	}

	for i := range plans {
		shard := elasticsearch.ShardInfo{
			Index: plans[i].Index,
			Shard: plans[i].Shard,
		}
		heatInfo := b.shardHeatMonitor.GetShardHeat(shard, plans[i].FromNode)
		plans[i].HeatScore = heatInfo.HeatScore
		plans[i].IsHotShard = heatInfo.IsHot
	}

	return plans
}

func (b *Balancer) sortPlansByHeat(plans []elasticsearch.MigrationPlan) []elasticsearch.MigrationPlan {
	if b.shardHeatMonitor == nil || !b.cfg.ShardHeat.Enabled {
		return plans
	}

	sort.Slice(plans, func(i, j int) bool {
		boostI := b.shardHeatMonitor.GetShardPriorityBoost(elasticsearch.ShardInfo{Index: plans[i].Index})
		boostJ := b.shardHeatMonitor.GetShardPriorityBoost(elasticsearch.ShardInfo{Index: plans[j].Index})

		scoreI := plans[i].HeatScore * boostI
		scoreJ := plans[j].HeatScore * boostJ

		return scoreI > scoreJ
	})

	return plans
}

func (b *Balancer) planForDiskWatermark(dist *elasticsearch.ShardDistribution) []elasticsearch.MigrationPlan {
	var plans []elasticsearch.MigrationPlan

	nodeWatermarks := make(map[string]struct{ low, high, flood float64 })
	for _, node := range dist.Nodes {
		low, high, flood := b.calculateDynamicWatermark(node)
		nodeWatermarks[node.NodeName] = struct{ low, high, flood float64 }{low, high, flood}

		node.DiskUsage.DynamicLow = low
		node.DiskUsage.DynamicHigh = high
		node.DiskUsage.DynamicFlood = flood
	}

	var highLoadNodes []*elasticsearch.NodeShardInfo
	var lowLoadNodes []*elasticsearch.NodeShardInfo

	for _, node := range dist.Nodes {
		wm := nodeWatermarks[node.NodeName]
		if node.DiskUsage.UsedPercent >= wm.high {
			highLoadNodes = append(highLoadNodes, node)
			b.logger.Debug("Node exceeds high watermark",
				zap.String("node", node.NodeName),
				zap.Float64("used_percent", node.DiskUsage.UsedPercent),
				zap.Float64("dynamic_high", wm.high),
				zap.Float64("base_high", b.cfg.DiskWatermark.High),
			)
		}
		if node.DiskUsage.UsedPercent < wm.low {
			lowLoadNodes = append(lowLoadNodes, node)
		}
	}

	if len(highLoadNodes) == 0 || len(lowLoadNodes) == 0 {
		return plans
	}

	sort.Slice(highLoadNodes, func(i, j int) bool {
		return highLoadNodes[i].DiskUsage.UsedPercent > highLoadNodes[j].DiskUsage.UsedPercent
	})

	sort.Slice(lowLoadNodes, func(i, j int) bool {
		return lowLoadNodes[i].DiskUsage.UsedPercent < lowLoadNodes[j].DiskUsage.UsedPercent
	})

	var lowLoadNodeNames []string
	for _, node := range lowLoadNodes {
		lowLoadNodeNames = append(lowLoadNodeNames, node.NodeName)
	}

	filteredLowLoadNodes := lowLoadNodeNames
	if b.loadMonitor != nil && b.cfg.LoadAwareness.AvoidHighLoadNodes {
		filteredLowLoadNodes = b.loadMonitor.FilterLowLoadNodes(lowLoadNodeNames)
		b.logger.Debug("Filtered candidate nodes",
			zap.Int("original", len(lowLoadNodeNames)),
			zap.Int("filtered", len(filteredLowLoadNodes)),
		)
	}

	for _, fromNode := range highLoadNodes {
		for _, shard := range fromNode.Shards {
			if shard.Prirep != "p" {
				continue
			}

			targetNodeName := b.selectBestTargetNode(shard, fromNode, filteredLowLoadNodes, dist, nodeWatermarks)
			if targetNodeName != "" {
				wm := nodeWatermarks[fromNode.NodeName]
				plans = append(plans, elasticsearch.MigrationPlan{
					Index:    shard.Index,
					Shard:    shard.Shard,
					FromNode: fromNode.NodeName,
					ToNode:   targetNodeName,
					Reason:   fmt.Sprintf("disk_watermark: %.2f%% > %.2f%% (dynamic, base: %.0f%%)", fromNode.DiskUsage.UsedPercent, wm.high, b.cfg.DiskWatermark.High),
				})
				break
			}
		}
	}

	return plans
}

func (b *Balancer) planForHotCold(dist *elasticsearch.ShardDistribution) []elasticsearch.MigrationPlan {
	var plans []elasticsearch.MigrationPlan

	if !b.cfg.HotCold.Enabled {
		return plans
	}

	hotNodes := make(map[string]*elasticsearch.NodeShardInfo)
	coldNodes := make(map[string]*elasticsearch.NodeShardInfo)

	for name, node := range dist.Nodes {
		if node.NodeType == "hot" {
			hotNodes[name] = node
		} else if node.NodeType == "cold" {
			coldNodes[name] = node
		}
	}

	if len(hotNodes) == 0 || len(coldNodes) == 0 {
		return plans
	}

	return plans
}

func (b *Balancer) selectBestTargetNode(shard elasticsearch.ShardInfo, fromNode *elasticsearch.NodeShardInfo, candidates []string, dist *elasticsearch.ShardDistribution, watermarks map[string]struct{ low, high, flood float64 }) string {
	if len(candidates) == 0 {
		return ""
	}

	type candidateScore struct {
		nodeName string
		score    float64
	}

	var scored []candidateScore
	for _, nodeName := range candidates {
		toNode, ok := dist.Nodes[nodeName]
		if !ok {
			continue
		}

		if !b.isValidMigration(shard, fromNode, toNode, dist) {
			continue
		}

		wm := watermarks[nodeName]
		if toNode.DiskUsage.UsedPercent >= wm.high {
			continue
		}

		score := 0.0
		score += toNode.DiskUsage.UsedPercent * 0.4
		score += float64(toNode.ShardCount) * 0.3

		if b.loadMonitor != nil {
			loadHistory := b.loadMonitor.GetNodeLoadHistory(nodeName)
			score += loadHistory.LoadScore * 100 * 0.3

			if b.cfg.LoadAwareness.AvoidHighLoadNodes && loadHistory.IsHighLoad {
				continue
			}
		}

		scored = append(scored, candidateScore{
			nodeName: nodeName,
			score:    score,
		})
	}

	if len(scored) == 0 {
		return ""
	}

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score < scored[j].score
	})

	bestNode := scored[0].nodeName
	if b.loadMonitor != nil {
		bestNode = b.loadMonitor.GetBestTargetNode([]string{bestNode})
	}

	return bestNode
}

func (b *Balancer) planForBalance(dist *elasticsearch.ShardDistribution) []elasticsearch.MigrationPlan {
	var plans []elasticsearch.MigrationPlan

	avgShards := dist.AvgShards
	threshold := math.Max(avgShards*0.1, 1)

	watermarks := make(map[string]struct{ low, high, flood float64 })
	for _, node := range dist.Nodes {
		low, high, flood := b.calculateDynamicWatermark(node)
		watermarks[node.NodeName] = struct{ low, high, flood float64 }{low, high, flood}
	}

	var overNodes []*elasticsearch.NodeShardInfo
	var underNodes []*elasticsearch.NodeShardInfo

	for _, node := range dist.Nodes {
		if float64(node.ShardCount) > avgShards+threshold {
			overNodes = append(overNodes, node)
		}
		if float64(node.ShardCount) < avgShards-threshold {
			underNodes = append(underNodes, node)
		}
	}

	if len(overNodes) == 0 || len(underNodes) == 0 {
		return plans
	}

	sort.Slice(overNodes, func(i, j int) bool {
		return overNodes[i].ShardCount > overNodes[j].ShardCount
	})

	sort.Slice(underNodes, func(i, j int) bool {
		return underNodes[i].ShardCount < underNodes[j].ShardCount
	})

	var underNodeNames []string
	for _, node := range underNodes {
		underNodeNames = append(underNodeNames, node.NodeName)
	}

	if b.loadMonitor != nil && b.cfg.LoadAwareness.AvoidHighLoadNodes {
		underNodeNames = b.loadMonitor.FilterLowLoadNodes(underNodeNames)
	}

	for _, fromNode := range overNodes {
		for _, shard := range fromNode.Shards {
			targetNodeName := b.selectBestTargetNode(shard, fromNode, underNodeNames, dist, watermarks)
			if targetNodeName != "" {
				plans = append(plans, elasticsearch.MigrationPlan{
					Index:    shard.Index,
					Shard:    shard.Shard,
					FromNode: fromNode.NodeName,
					ToNode:   targetNodeName,
					Reason:   fmt.Sprintf("balance: %d > %.0f + %.0f", fromNode.ShardCount, avgShards, threshold),
				})
				if toNode, ok := dist.Nodes[targetNodeName]; ok {
					toNode.ShardCount++
				}
				fromNode.ShardCount--
				break
			}
		}
	}

	return plans
}

func (b *Balancer) isValidMigration(shard elasticsearch.ShardInfo, fromNode, toNode *elasticsearch.NodeShardInfo, dist *elasticsearch.ShardDistribution) bool {
	if fromNode.NodeName == toNode.NodeName {
		return false
	}

	if b.cfg.HotCold.Enabled {
		if fromNode.NodeType != toNode.NodeType {
			return false
		}
	}

	if targetNode, ok := dist.Nodes[toNode.NodeName]; ok {
		for _, s := range targetNode.Shards {
			if s.Index == shard.Index && s.Shard == shard.Shard {
				return false
			}
		}
	}

	return true
}

func (b *Balancer) ExecuteMigrations(ctx context.Context, plans []elasticsearch.MigrationPlan) error {
	for _, plan := range plans {
		shardNum, err := strconv.Atoi(plan.Shard)
		if err != nil {
			b.logger.Error("invalid shard number", zap.String("shard", plan.Shard), zap.Error(err))
			continue
		}

		b.logger.Info("executing shard migration",
			zap.String("index", plan.Index),
			zap.String("shard", plan.Shard),
			zap.String("from", plan.FromNode),
			zap.String("to", plan.ToNode),
			zap.String("reason", plan.Reason),
		)

		if err := b.client.MoveShard(ctx, plan.Index, shardNum, plan.FromNode, plan.ToNode); err != nil {
			b.logger.Error("failed to move shard",
				zap.String("index", plan.Index),
				zap.String("shard", plan.Shard),
				zap.Error(err),
			)
			continue
		}

		b.logger.Info("shard migration initiated",
			zap.String("index", plan.Index),
			zap.String("shard", plan.Shard),
		)
	}

	return nil
}

func (b *Balancer) RunBalanceCycle(ctx context.Context) (*BalanceResult, error) {
	b.logger.Info("starting balance cycle")

	health, err := b.client.GetClusterHealth(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get cluster health: %w", err)
	}

	if health.RelocatingShards > 0 {
		b.logger.Info("skipping balance cycle - relocations in progress",
			zap.Int("relocating_shards", health.RelocatingShards),
		)
		return &BalanceResult{
			Message: "Relocations in progress, skipping cycle",
		}, nil
	}

	plans, err := b.GenerateMigrationPlan(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to generate migration plan: %w", err)
	}

	if len(plans) == 0 {
		b.logger.Info("no migrations needed")
		return &BalanceResult{
			MigrationsPlanned: 0,
			Message:           "Cluster is balanced",
		}, nil
	}

	b.logger.Info("generated migration plan", zap.Int("count", len(plans)))

	if err := b.ExecuteMigrations(ctx, plans); err != nil {
		return nil, fmt.Errorf("failed to execute migrations: %w", err)
	}

	return &BalanceResult{
		MigrationsPlanned: len(plans),
		Migrations:        plans,
		Message:           fmt.Sprintf("Initiated %d migrations", len(plans)),
	}, nil
}

type BalanceResult struct {
	MigrationsPlanned int                           `json:"migrations_planned"`
	Migrations        []elasticsearch.MigrationPlan `json:"migrations"`
	Message           string                        `json:"message"`
}

func (b *Balancer) SimulateMigration(ctx context.Context) (*elasticsearch.MigrationSimulationResult, error) {
	b.logger.Info("starting migration simulation")

	beforeDist, err := b.AnalyzeDistribution(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to analyze distribution: %w", err)
	}

	plans, err := b.GenerateMigrationPlan(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to generate migration plan: %w", err)
	}

	afterDist := b.simulateDistributionAfterMigration(beforeDist, plans)

	metrics := b.calculateSimulationMetrics(beforeDist, afterDist, plans)

	totalBytes := int64(0)
	for _, plan := range plans {
		totalBytes += plan.EstimatedSize
	}

	speedBytesPerSec := int64(50 * 1024 * 1024)
	if b.speedCtrl != nil {
		if currentSpeed, err := parseSpeedString(b.speedCtrl.GetCurrentSpeed()); err == nil {
			speedBytesPerSec = currentSpeed
		}
	}

	estimatedTime := float64(totalBytes) / float64(speedBytesPerSec)
	if speedBytesPerSec <= 0 {
		estimatedTime = 0
	}

	var warnings []string
	if metrics.AfterMaxDiskUsage >= b.cfg.DiskWatermark.High {
		warnings = append(warnings,
			fmt.Sprintf("After migration, max disk usage (%.2f%%) still exceeds high watermark (%.2f%%)",
				metrics.AfterMaxDiskUsage, b.cfg.DiskWatermark.High))
	}
	if metrics.ImbalanceImprovement < 0 {
		warnings = append(warnings,
			fmt.Sprintf("Migration may increase imbalance by %.2f%%",
				-metrics.ImbalanceImprovement))
	}

	return &elasticsearch.MigrationSimulationResult{
		Plans:                plans,
		BeforeDistribution:   beforeDist,
		AfterDistribution:    afterDist,
		ImprovementMetrics:   metrics,
		EstimatedTimeSeconds: estimatedTime,
		EstimatedTotalBytes:  totalBytes,
		Warnings:             warnings,
	}, nil
}

func (b *Balancer) simulateDistributionAfterMigration(original *elasticsearch.ShardDistribution, plans []elasticsearch.MigrationPlan) *elasticsearch.ShardDistribution {
	simDist := &elasticsearch.ShardDistribution{
		Nodes:       make(map[string]*elasticsearch.NodeShardInfo),
		TotalShards: original.TotalShards,
		AvgShards:   original.AvgShards,
		Imbalance:   original.Imbalance,
	}

	for nodeName, node := range original.Nodes {
		simNode := &elasticsearch.NodeShardInfo{
			NodeName:   node.NodeName,
			ShardCount: node.ShardCount,
			Indices:    make([]string, len(node.Indices)),
			Shards:     make([]elasticsearch.ShardInfo, len(node.Shards)),
			DiskUsage:  node.DiskUsage,
			NodeType:   node.NodeType,
		}
		copy(simNode.Indices, node.Indices)
		copy(simNode.Shards, node.Shards)
		simDist.Nodes[nodeName] = simNode
	}

	for _, plan := range plans {
		fromNode, ok := simDist.Nodes[plan.FromNode]
		if !ok {
			continue
		}
		toNode, ok := simDist.Nodes[plan.ToNode]
		if !ok {
			continue
		}

		for i, shard := range fromNode.Shards {
			if shard.Index == plan.Index && shard.Shard == plan.Shard {
				fromNode.Shards = append(fromNode.Shards[:i], fromNode.Shards[i+1:]...)
				fromNode.ShardCount--

				shard.Node = plan.ToNode
				toNode.Shards = append(toNode.Shards, shard)
				toNode.ShardCount++

				hasIndex := false
				for _, idx := range toNode.Indices {
					if idx == plan.Index {
						hasIndex = true
						break
					}
				}
				if !hasIndex {
					toNode.Indices = append(toNode.Indices, plan.Index)
				}

				indexFound := false
				for _, idx := range fromNode.Indices {
					if idx == plan.Index {
						indexFound = true
						break
					}
				}
				if indexFound {
					stillHasIndex := false
					for _, s := range fromNode.Shards {
						if s.Index == plan.Index {
							stillHasIndex = true
							break
						}
					}
					if !stillHasIndex {
						for i, idx := range fromNode.Indices {
							if idx == plan.Index {
								fromNode.Indices = append(fromNode.Indices[:i], fromNode.Indices[i+1:]...)
								break
							}
						}
					}
				}

				estimatedSize := plan.EstimatedSize
				if estimatedSize <= 0 {
					estimatedSize = 100 * 1024 * 1024
				}
				fromNode.DiskUsage.UsedBytes -= estimatedSize
				fromNode.DiskUsage.AvailableBytes += estimatedSize
				fromNode.DiskUsage.UsedPercent = float64(fromNode.DiskUsage.UsedBytes) / float64(fromNode.DiskUsage.TotalBytes) * 100

				toNode.DiskUsage.UsedBytes += estimatedSize
				toNode.DiskUsage.AvailableBytes -= estimatedSize
				toNode.DiskUsage.UsedPercent = float64(toNode.DiskUsage.UsedBytes) / float64(toNode.DiskUsage.TotalBytes) * 100

				break
			}
		}
	}

	maxShards := 0
	minShards := 0
	first := true
	for _, node := range simDist.Nodes {
		if first {
			maxShards = node.ShardCount
			minShards = node.ShardCount
			first = false
		} else {
			if node.ShardCount > maxShards {
				maxShards = node.ShardCount
			}
			if node.ShardCount < minShards {
				minShards = node.ShardCount
			}
		}
	}
	simDist.MaxShards = maxShards
	simDist.MinShards = minShards

	if simDist.AvgShards > 0 {
		simDist.Imbalance = float64(maxShards-minShards) / simDist.AvgShards
	}

	return simDist
}

func (b *Balancer) calculateSimulationMetrics(before, after *elasticsearch.ShardDistribution, plans []elasticsearch.MigrationPlan) *elasticsearch.SimulationMetrics {
	metrics := &elasticsearch.SimulationMetrics{}

	metrics.BeforeImbalance = before.Imbalance
	metrics.AfterImbalance = after.Imbalance
	if metrics.BeforeImbalance > 0 {
		metrics.ImbalanceImprovement = (metrics.BeforeImbalance - metrics.AfterImbalance) / metrics.BeforeImbalance * 100
	}

	maxBefore := 0.0
	maxAfter := 0.0
	for _, node := range before.Nodes {
		if node.DiskUsage.UsedPercent > maxBefore {
			maxBefore = node.DiskUsage.UsedPercent
		}
	}
	for _, node := range after.Nodes {
		if node.DiskUsage.UsedPercent > maxAfter {
			maxAfter = node.DiskUsage.UsedPercent
		}
	}
	metrics.BeforeMaxDiskUsage = maxBefore
	metrics.AfterMaxDiskUsage = maxAfter
	if metrics.BeforeMaxDiskUsage > 0 {
		metrics.DiskUsageImprovement = (metrics.BeforeMaxDiskUsage - metrics.AfterMaxDiskUsage) / metrics.BeforeMaxDiskUsage * 100
	}

	wmHigh := b.cfg.DiskWatermark.High
	for _, node := range before.Nodes {
		if node.DiskUsage.UsedPercent >= wmHigh {
			metrics.NodesOverHighWatermarkBefore++
		}
	}
	for _, node := range after.Nodes {
		if node.DiskUsage.UsedPercent >= wmHigh {
			metrics.NodesOverHighWatermarkAfter++
		}
	}

	hotShardsBefore := 0
	hotShardsAfter := 0
	if b.shardHeatMonitor != nil && b.loadMonitor != nil {
		hotIndices := make(map[string]bool)
		for _, idx := range b.shardHeatMonitor.GetHotIndices() {
			hotIndices[idx] = true
		}

		highLoadNodes := make(map[string]bool)
		for nodeName := range before.Nodes {
			history := b.loadMonitor.GetNodeLoadHistory(nodeName)
			if history.IsHighLoad {
				highLoadNodes[nodeName] = true
			}
		}

		for nodeName, node := range before.Nodes {
			if highLoadNodes[nodeName] {
				for _, shard := range node.Shards {
					if hotIndices[shard.Index] {
						hotShardsBefore++
					}
				}
			}
		}

		for nodeName, node := range after.Nodes {
			if highLoadNodes[nodeName] {
				for _, shard := range node.Shards {
					if hotIndices[shard.Index] {
						hotShardsAfter++
					}
				}
			}
		}
	}

	metrics.BeforeHotShardsOnHighLoad = hotShardsBefore
	metrics.AfterHotShardsOnHighLoad = hotShardsAfter
	if hotShardsBefore > 0 {
		metrics.HotShardImprovement = float64(hotShardsBefore-hotShardsAfter) / float64(hotShardsBefore) * 100
	}

	balanceScore := 100.0
	if metrics.ImbalanceImprovement > 0 {
		balanceScore += metrics.ImbalanceImprovement * 0.4
	} else {
		balanceScore += metrics.ImbalanceImprovement * 0.6
	}

	diskScore := 100.0
	if metrics.DiskUsageImprovement > 0 {
		diskScore += metrics.DiskUsageImprovement * 0.4
	} else {
		diskScore += metrics.DiskUsageImprovement * 0.6
	}

	hotShardScore := 100.0
	if metrics.HotShardImprovement > 0 {
		hotShardScore += metrics.HotShardImprovement * 0.3
	} else if metrics.HotShardImprovement < 0 {
		hotShardScore += metrics.HotShardImprovement * 0.5
	}

	watermarkReduction := metrics.NodesOverHighWatermarkBefore - metrics.NodesOverHighWatermarkAfter
	watermarkScore := 100.0
	if watermarkReduction > 0 {
		watermarkScore += float64(watermarkReduction) * 10
	} else if watermarkReduction < 0 {
		watermarkScore += float64(watermarkReduction) * 15
	}

	metrics.OverallScore = (balanceScore*0.35 + diskScore*0.35 + hotShardScore*0.15 + watermarkScore*0.15)
	if metrics.OverallScore < 0 {
		metrics.OverallScore = 0
	}
	if metrics.OverallScore > 100 {
		metrics.OverallScore = 100
	}

	return metrics
}

func parseSpeedString(speed string) (int64, error) {
	if len(speed) == 0 {
		return 0, nil
	}

	numStr := ""
	unit := ""
	for i, c := range speed {
		if c >= '0' && c <= '9' || c == '.' {
			numStr += string(c)
		} else {
			unit = speed[i:]
			break
		}
	}

	num, err := strconv.ParseFloat(numStr, 64)
	if err != nil {
		return 0, fmt.Errorf("invalid speed value: %s", numStr)
	}

	switch unit {
	case "b", "B", "":
		return int64(num), nil
	case "kb", "KB", "Kb":
		return int64(num * 1024), nil
	case "mb", "MB", "Mb":
		return int64(num * 1024 * 1024), nil
	case "gb", "GB", "Gb":
		return int64(num * 1024 * 1024 * 1024), nil
	default:
		return int64(num), nil
	}
}

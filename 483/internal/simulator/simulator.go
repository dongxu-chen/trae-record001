package simulator

import (
	"fmt"
	"math"
	"sort"
	"time"

	"kafka-lag-analyzer/internal/analyzer"
	"kafka-lag-analyzer/internal/config"
)

type Simulator interface {
	SimulateConsumerAddition(groupID string, additionalConsumers int, analysis *analyzer.ConsumerGroupAnalysis, predictor func(string) (*analyzer.GroupProgressPrediction, error)) (*analyzer.ConsumerSimulation, error)
	GenerateRebalancePlan(groupID string, analysis *analyzer.ConsumerGroupAnalysis) (*analyzer.RebalancePlan, error)
}

type lagSimulator struct {
	cfg      *config.AnalyzerConfig
	kafkaCfg *config.KafkaConfig
}

func NewSimulator(cfg *config.AnalyzerConfig, kafkaCfg *config.KafkaConfig) Simulator {
	return &lagSimulator{
		cfg:      cfg,
		kafkaCfg: kafkaCfg,
	}
}

func (s *lagSimulator) SimulateConsumerAddition(
	groupID string,
	additionalConsumers int,
	analysis *analyzer.ConsumerGroupAnalysis,
	predictor func(string) (*analyzer.GroupProgressPrediction, error),
) (*analyzer.ConsumerSimulation, error) {
	if analysis == nil {
		return nil, fmt.Errorf("no analysis available")
	}

	if additionalConsumers < 1 {
		return nil, fmt.Errorf("additional consumers must be >= 1")
	}

	originalMemberCount := analysis.MemberCount
	if originalMemberCount == 0 {
		originalMemberCount = 1
	}
	simulatedMemberCount := originalMemberCount + additionalConsumers

	sim := &analyzer.ConsumerSimulation{
		GroupID:              groupID,
		OriginalMemberCount:  originalMemberCount,
		SimulatedMemberCount: simulatedMemberCount,
		OriginalTotalLag:     analysis.TotalLag,
		TopicSimulations:     make(map[string]analyzer.TopicSimulation),
		Assumptions: []string{
			"所有消费者处理能力均等",
			"消息生产速率保持稳定",
			"分区在消费者间均匀分配",
			"不考虑再平衡期间的消费停滞",
			"不考虑网络延迟变化",
		},
	}

	totalSimulatedLag := 0.0
	maxOriginalTime := time.Duration(0)
	maxSimulatedTime := time.Duration(0)

	for topic, topicLag := range analysis.Topics {
		topicSim := s.simulateTopic(topicLag, originalMemberCount, simulatedMemberCount)
		sim.TopicSimulations[topic] = topicSim
		totalSimulatedLag += topicSim.SimulatedTotalLag

		if topicSim.OriginalTimeToClear > maxOriginalTime {
			maxOriginalTime = topicSim.OriginalTimeToClear
		}
		if topicSim.EstimatedTimeToClear > maxSimulatedTime {
			maxSimulatedTime = topicSim.EstimatedTimeToClear
		}
	}

	sim.SimulatedTotalLag = totalSimulatedLag

	if analysis.TotalLag > 0 {
		sim.ImprovementPercent = 100.0 * (1.0 - totalSimulatedLag/float64(analysis.TotalLag))
	}
	if sim.ImprovementPercent < 0 {
		sim.ImprovementPercent = 0
	}

	if predictor != nil {
		originalPred, _ := predictor(groupID)
		if originalPred != nil && originalPred.OverallEstimatedTimeToClear < time.Duration(math.MaxInt64) {
			maxOriginalTime = originalPred.OverallEstimatedTimeToClear
			ratio := float64(originalMemberCount) / float64(simulatedMemberCount)
			maxSimulatedTime = time.Duration(float64(maxOriginalTime) * ratio)
		}
	}

	sim.EstimatedTimeSaved = maxOriginalTime - maxSimulatedTime
	if sim.EstimatedTimeSaved < 0 {
		sim.EstimatedTimeSaved = 0
	}

	actualPartitions := s.totalPartitions(analysis)
	if simulatedMemberCount > actualPartitions {
		sim.Assumptions = append(sim.Assumptions,
			fmt.Sprintf("注意: 消费者数量(%d)超过分区总数(%d)，部分消费者将空闲", simulatedMemberCount, actualPartitions))
	}

	return sim, nil
}

func (s *lagSimulator) simulateTopic(
	topicLag *analyzer.TopicLag,
	originalMemberCount int,
	simulatedMemberCount int,
) analyzer.TopicSimulation {
	sim := analyzer.TopicSimulation{
		Topic:             topicLag.Topic,
		OriginalTotalLag:  topicLag.TotalLag,
		PartitionDistribution: make(map[int32]string),
	}

	totalPartitions := topicLag.PartitionCount
	if totalPartitions == 0 {
		return sim
	}

	partitions := make([]analyzer.PartitionLag, len(topicLag.Partitions))
	copy(partitions, topicLag.Partitions)

	sort.Slice(partitions, func(i, j int) bool {
		return partitions[i].Lag > partitions[j].Lag
	})

	effectiveMembers := simulatedMemberCount
	if simulatedMemberCount > totalPartitions {
		effectiveMembers = totalPartitions
	}

	memberLoads := make([]int64, simulatedMemberCount)
	memberPartitions := make(map[string][]int32)

	for i, partLag := range partitions {
		memberIdx := 0
		minLoad := int64(math.MaxInt64)
		for m := 0; m < effectiveMembers; m++ {
			if memberLoads[m] < minLoad {
				minLoad = memberLoads[m]
				memberIdx = m
			}
		}

		memberID := fmt.Sprintf("consumer-%d", memberIdx)
		memberLoads[memberIdx] += partLag.Lag
		sim.PartitionDistribution[partLag.Partition] = memberID
		memberPartitions[memberID] = append(memberPartitions[memberID], partLag.Partition)
	}

	maxMemberLag := int64(0)
	for _, load := range memberLoads {
		if load > maxMemberLag {
			maxMemberLag = load
		}
	}
	sim.SimulatedTotalLag = float64(maxMemberLag) * float64(effectiveMembers)

	if topicLag.TotalLag > 0 {
		sim.ImprovementPercent = 100.0 * (1.0 - sim.SimulatedTotalLag/float64(topicLag.TotalLag))
	}
	if sim.ImprovementPercent < 0 {
		sim.ImprovementPercent = 0
	}

	totalConsumptionRate := 0.0
	for _, p := range partitions {
		historyLen := 10
		if p.LagChangeRate != 0 && p.PreviousLag > 0 {
			rate := (float64(p.CurrentOffset) / float64(historyLen)) / 15.0
			totalConsumptionRate += rate
		}
	}
	if totalConsumptionRate > 0 && sim.SimulatedTotalLag > 0 {
		sim.EstimatedTimeToClear = time.Duration(sim.SimulatedTotalLag/totalConsumptionRate) * time.Second
		sim.OriginalTimeToClear = time.Duration(float64(topicLag.TotalLag)/totalConsumptionRate) * time.Second
	}

	return sim
}

func (s *lagSimulator) GenerateRebalancePlan(
	groupID string,
	analysis *analyzer.ConsumerGroupAnalysis,
) (*analyzer.RebalancePlan, error) {
	if analysis == nil {
		return nil, fmt.Errorf("no analysis available")
	}

	plan := &analyzer.RebalancePlan{
		GroupID:        groupID,
		HotPartitions:  []analyzer.HotPartitionAction{},
		TopicsToExpand: []analyzer.TopicExpansion{},
	}

	totalOriginalLag := analysis.TotalLag
	totalHotLag := int64(0)

	for _, partLag := range analysis.HotPartitions {
		action := s.analyzeHotPartition(partLag, analysis)
		if action.Action != "" {
			plan.HotPartitions = append(plan.HotPartitions, action)
			totalHotLag += partLag.Lag
		}
	}

	for topic, topicLag := range analysis.Topics {
		expansion := s.analyzeTopicExpansion(topic, topicLag, analysis)
		if expansion != nil {
			plan.TopicsToExpand = append(plan.TopicsToExpand, *expansion)
			plan.PartitionCountIncrease += expansion.RecommendedPartitions - expansion.CurrentPartitions
			plan.RecommendedPartitions += expansion.RecommendedPartitions
		}
	}

	if totalOriginalLag > 0 {
		plan.EstimatedImprovement = 100.0 * float64(totalHotLag) / float64(totalOriginalLag)
	}

	plan.RebalanceImpact = s.estimateRebalanceImpact(plan, analysis)

	return plan, nil
}

func (s *lagSimulator) analyzeHotPartition(
	partLag analyzer.PartitionLag,
	analysis *analyzer.ConsumerGroupAnalysis,
) analyzer.HotPartitionAction {
	action := analyzer.HotPartitionAction{
		Topic:          partLag.Topic,
		Partition:      partLag.Partition,
		CurrentLag:     partLag.Lag,
		TargetMembers:  []string{},
	}

	if partLag.AvgMessageSize > 0 {
		action.CurrentLoad = float64(partLag.Lag) * partLag.AvgMessageSize
	} else {
		action.CurrentLoad = float64(partLag.Lag)
	}

	topicLag, ok := analysis.Topics[partLag.Topic]
	if !ok {
		return action
	}

	avgLag := topicLag.AvgLag
	if avgLag == 0 {
		avgLag = 1
	}
	lagRatio := float64(partLag.Lag) / avgLag

	memberCount := analysis.MemberCount
	if memberCount == 0 {
		memberCount = 1
	}

	switch {
	case lagRatio > 10.0 && partLag.Lag > s.cfg.LagThreshold*10:
		action.Action = "split"
		action.SplitInto = int(math.Min(8, math.Ceil(lagRatio/2.0)))
		action.ExpectedLag = float64(partLag.Lag) / float64(action.SplitInto) * 1.5
		action.ImprovementPct = 100.0 * (1.0 - action.ExpectedLag/float64(partLag.Lag))
		action.Reason = fmt.Sprintf("lag是均值的%.1f倍，建议拆分为%d个分区", lagRatio, action.SplitInto)

	case lagRatio > 3.0 && analysis.MemberCount < topicLag.PartitionCount:
		action.Action = "redistribute"
		action.SplitInto = 1
		action.TargetMembers = s.findTargetMembers(partLag, analysis)
		action.ExpectedLag = avgLag * 1.2
		action.ImprovementPct = 100.0 * (1.0 - action.ExpectedLag/float64(partLag.Lag))
		action.Reason = "分区分配不均，建议重分配到负载较轻的消费者"

	default:
		action.Action = "monitor"
		action.SplitInto = 1
		action.ExpectedLag = float64(partLag.Lag)
		action.ImprovementPct = 0
		action.Reason = "监控中，尚未达到干预阈值"
	}

	return action
}

func (s *lagSimulator) analyzeTopicExpansion(
	topic string,
	topicLag *analyzer.TopicLag,
	analysis *analyzer.ConsumerGroupAnalysis,
) *analyzer.TopicExpansion {
	if topicLag.TotalLag == 0 {
		return nil
	}

	memberCount := analysis.MemberCount
	if memberCount == 0 {
		memberCount = 1
	}

	avgMsgSize := topicLag.AvgMessageSize
	lagPerPartition := float64(topicLag.TotalLag) / float64(topicLag.PartitionCount)

	ratio := float64(topicLag.PartitionCount) / float64(memberCount)

	var recommended int
	var reason string

	switch {
	case topicLag.PartitionCount <= memberCount && lagPerPartition > float64(s.cfg.LagThreshold):
		recommended = int(math.Min(
			float64(memberCount*2),
			math.Ceil(float64(topicLag.TotalLag)/float64(s.cfg.LagThreshold)),
		))
		if recommended <= topicLag.PartitionCount {
			recommended = topicLag.PartitionCount + int(math.Max(2, float64(topicLag.PartitionCount)*0.5))
		}
		reason = fmt.Sprintf("分区数(%d)<=消费者数(%d)且每个分区平均lag=%.0f超过阈值",
			topicLag.PartitionCount, memberCount, lagPerPartition)

	case ratio < 1.5 && lagPerPartition > float64(s.cfg.LagThreshold)*0.5:
		recommended = int(math.Ceil(float64(memberCount) * 2.0))
		if recommended <= topicLag.PartitionCount {
			recommended = topicLag.PartitionCount + 2
		}
		reason = fmt.Sprintf("分区/消费者比=%.1f<1.5，建议增加分区提高并行度", ratio)

	case avgMsgSize > 512*1024 && lagPerPartition > float64(s.cfg.LagThreshold)*0.3:
		recommended = int(math.Ceil(float64(topicLag.PartitionCount) * 1.5))
		reason = fmt.Sprintf("大消息(avg=%.0fKB)导致处理缓慢，建议增加分区减少单分区负载", avgMsgSize/1024)

	default:
		return nil
	}

	expectedImprovement := 100.0 * (1.0 - float64(topicLag.PartitionCount)/float64(recommended))
	if expectedImprovement < 10 {
		expectedImprovement = 10
	}
	if expectedImprovement > 80 {
		expectedImprovement = 80
	}

	return &analyzer.TopicExpansion{
		Topic:                 topic,
		CurrentPartitions:     topicLag.PartitionCount,
		RecommendedPartitions: recommended,
		Reason:                reason,
		ExpectedImprovement:   expectedImprovement,
	}
}

func (s *lagSimulator) findTargetMembers(partLag analyzer.PartitionLag, analysis *analyzer.ConsumerGroupAnalysis) []string {
	memberLoads := make(map[string]int64)
	for _, topicLag := range analysis.Topics {
		for _, p := range topicLag.Partitions {
			if p.Member != "" {
				memberLoads[p.Member] += p.Lag
			}
		}
	}

	if len(memberLoads) == 0 {
		return nil
	}

	type memberInfo struct {
		id   string
		load int64
	}
	members := make([]memberInfo, 0, len(memberLoads))
	for id, load := range memberLoads {
		members = append(members, memberInfo{id, load})
	}

	sort.Slice(members, func(i, j int) bool {
		return members[i].load < members[j].load
	})

	targets := make([]string, 0, 2)
	for i := 0; i < len(members) && i < 2; i++ {
		targets = append(targets, members[i].id)
	}

	return targets
}

func (s *lagSimulator) estimateRebalanceImpact(
	plan *analyzer.RebalancePlan,
	analysis *analyzer.ConsumerGroupAnalysis,
) analyzer.RebalanceImpact {
	impact := analyzer.RebalanceImpact{}

	totalBytes := int64(0)
	partitionsToMove := 0

	for _, action := range plan.HotPartitions {
		if topicLag, ok := analysis.Topics[action.Topic]; ok {
			var logSize int64
			for _, p := range topicLag.Partitions {
				if p.Partition == action.Partition {
					logSize = p.LogSize
					break
				}
			}
			if logSize == 0 {
				logSize = int64(action.CurrentLag * 1024)
			}
			totalBytes += logSize
		}
		partitionsToMove++
	}

	impact.DataMovementBytes = totalBytes

	baseDowntime := time.Duration(10) * time.Second
	if analysis.MemberCount > 5 {
		baseDowntime += time.Duration(analysis.MemberCount) * time.Second
	}
	if partitionsToMove > 10 {
		baseDowntime += time.Duration(partitionsToMove/5) * time.Second
	}
	if totalBytes > 10*1024*1024*1024 {
		baseDowntime += 30 * time.Second
	}

	impact.DowntimeEstimate = baseDowntime

	switch {
	case partitionsToMove > 20 || totalBytes > 100*1024*1024*1024:
		impact.RiskLevel = "high"
		impact.ConsumerImpact = "所有消费者暂停消费1-5分钟，期间lag可能增长"
	case partitionsToMove > 5 || totalBytes > 10*1024*1024*1024:
		impact.RiskLevel = "medium"
		impact.ConsumerImpact = "再平衡期间消费暂停30-60秒"
	default:
		impact.RiskLevel = "low"
		impact.ConsumerImpact = "再平衡期间消费暂停10-30秒"
	}

	return impact
}

func (s *lagSimulator) totalPartitions(analysis *analyzer.ConsumerGroupAnalysis) int {
	total := 0
	for _, topicLag := range analysis.Topics {
		total += topicLag.PartitionCount
	}
	return total
}

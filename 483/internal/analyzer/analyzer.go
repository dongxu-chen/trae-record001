package analyzer

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"

	"kafka-lag-analyzer/internal/config"
	"kafka-lag-analyzer/internal/kafka"
	"kafka-lag-analyzer/internal/predictor"
	"kafka-lag-analyzer/internal/prober"
	"kafka-lag-analyzer/internal/simulator"
)

type lagAnalyzer struct {
	kafkaClient kafka.Client
	prober      prober.Prober
	predictor   predictor.Predictor
	simulator   simulator.Simulator
	cfg         *config.AnalyzerConfig
	kafkaCfg    *config.KafkaConfig
	history     map[string]map[string]map[int32][]HistoricalLag
	latest      []*ConsumerGroupAnalysis
	mu          sync.RWMutex
}

func NewAnalyzer(kafkaClient kafka.Client, prober prober.Prober, cfg *config.AnalyzerConfig, kafkaCfg *config.KafkaConfig) Analyzer {
	return &lagAnalyzer{
		kafkaClient: kafkaClient,
		prober:      prober,
		predictor:   predictor.NewPredictor(cfg),
		simulator:   simulator.NewSimulator(cfg, kafkaCfg),
		cfg:         cfg,
		kafkaCfg:    kafkaCfg,
		history:     make(map[string]map[string]map[int32][]HistoricalLag),
	}
}

func (a *lagAnalyzer) Analyze() ([]*ConsumerGroupAnalysis, error) {
	groupIDs, err := a.kafkaClient.ListConsumerGroups()
	if err != nil {
		return nil, fmt.Errorf("failed to list consumer groups: %w", err)
	}

	var wg sync.WaitGroup
	results := make(chan *ConsumerGroupAnalysis, len(groupIDs))
	errors := make(chan error, len(groupIDs))

	for _, groupID := range groupIDs {
		wg.Add(1)
		go func(gid string) {
			defer wg.Done()
			analysis, err := a.analyzeConsumerGroup(gid)
			if err != nil {
				errors <- err
				return
			}
			results <- analysis
		}(groupID)
	}

	wg.Wait()
	close(results)
	close(errors)

	var analyses []*ConsumerGroupAnalysis
	for analysis := range results {
		analyses = append(analyses, analysis)
	}

	a.mu.Lock()
	a.latest = analyses
	a.mu.Unlock()

	return analyses, nil
}

func (a *lagAnalyzer) analyzeConsumerGroup(groupID string) (*ConsumerGroupAnalysis, error) {
	groupInfo, err := a.kafkaClient.DescribeConsumerGroup(groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to describe group %s: %w", groupID, err)
	}

	offsets, err := a.kafkaClient.GetConsumerGroupOffsets(groupID, a.cfgTopics())
	if err != nil {
		return nil, fmt.Errorf("failed to get offsets for group %s: %w", groupID, err)
	}

	analysis := &ConsumerGroupAnalysis{
		GroupID:     groupID,
		State:       groupInfo.State,
		MemberCount: len(groupInfo.Members),
		Topics:      make(map[string]*TopicLag),
		Timestamp:   time.Now(),
	}

	memberPartitions := a.buildMemberPartitionMap(groupInfo)

	for topic, partitionMap := range offsets.Partitions {
		logSizes, _ := a.kafkaClient.GetTopicPartitionLogSizes(topic)

		topicLag := a.analyzeTopic(groupID, topic, partitionMap, memberPartitions, logSizes)
		analysis.Topics[topic] = topicLag
		analysis.TotalLag += topicLag.TotalLag

		for _, p := range topicLag.Partitions {
			if p.Lag > a.cfg.LagThreshold*int64(math.Max(1, int64(a.cfg.HotspotThreshold*10))) {
				analysis.HotPartitions = append(analysis.HotPartitions, p)
			}
		}
	}

	sort.Slice(analysis.HotPartitions, func(i, j int) bool {
		return analysis.HotPartitions[i].Lag > analysis.HotPartitions[j].Lag
	})

	if len(analysis.HotPartitions) > 10 {
		analysis.HotPartitions = analysis.HotPartitions[:10]
	}

	analysis.DelayAttributions = a.attributeDelays(analysis)
	analysis.Recommendations = a.generateRecommendations(analysis)
	analysis.OverallStatus = a.determineOverallStatus(analysis)

	return analysis, nil
}

func (a *lagAnalyzer) analyzeTopic(groupID, topic string, partitionMap map[int32]kafka.PartitionOffset, memberPartitions map[string]map[string][]int32, logSizes map[int32]int64) *TopicLag {
	topicLag := &TopicLag{
		Topic:          topic,
		ConsumerGroup:  groupID,
		PartitionCount: len(partitionMap),
		Partitions:     make([]PartitionLag, 0, len(partitionMap)),
	}

	var totalLag int64
	var maxLag int64
	var minLag int64 = math.MaxInt64
	var totalLogSize int64
	lagValues := make([]int64, 0, len(partitionMap))

	for partition, offset := range partitionMap {
		history := a.getHistory(groupID, topic, partition)
		previousLag := int64(0)
		if len(history) > 0 {
			previousLag = history[len(history)-1].Lag
		}

		changeRate := 0.0
		if previousLag > 0 {
			changeRate = float64(offset.Lag-previousLag) / float64(previousLag)
		}

		member := a.findMemberForPartition(topic, partition, memberPartitions)

		status := StatusNormal
		switch {
		case offset.Lag >= a.cfg.LagThreshold*10:
			status = StatusCritical
		case offset.Lag >= a.cfg.LagThreshold:
			status = StatusWarning
		}

		logSize := int64(0)
		if ls, ok := logSizes[partition]; ok {
			logSize = ls
		}
		totalLogSize += logSize

		avgMsgSize := offset.AvgMessageSize
		if avgMsgSize == 0 && logSize > 0 && offset.EndOffset > offset.Offset {
			avgMsgSize = float64(logSize) / float64(offset.EndOffset-offset.Offset)
		}

		var brokerRTT time.Duration
		if a.prober != nil {
			if probeResult := a.prober.GetLatestResult(); probeResult != nil {
				if prtt, ok := probeResult.PartitionRTTs[topic]; ok {
					if partRTT, ok2 := prtt[partition]; ok2 {
						brokerRTT = partRTT.RTT
					}
				}
			}
		}

		pLag := PartitionLag{
			Topic:          topic,
			Partition:      partition,
			ConsumerGroup:  groupID,
			CurrentOffset:  offset.Offset,
			EndOffset:      offset.EndOffset,
			Lag:            offset.Lag,
			PreviousLag:    previousLag,
			LagChangeRate:  changeRate,
			Status:         status,
			Member:         member,
			LastCommit:     offset.LastCommitTime,
			LogSize:        logSize,
			AvgMessageSize: avgMsgSize,
			BrokerRTT:      brokerRTT,
		}

		a.updateHistory(groupID, topic, partition, HistoricalLag{
			Timestamp: time.Now(),
			Lag:       offset.Lag,
			Offset:    offset.Offset,
			EndOffset: offset.EndOffset,
		})

		topicLag.Partitions = append(topicLag.Partitions, pLag)
		totalLag += offset.Lag
		if offset.Lag > maxLag {
			maxLag = offset.Lag
		}
		if offset.Lag < minLag {
			minLag = offset.Lag
		}
		lagValues = append(lagValues, offset.Lag)
	}

	topicLag.TotalLag = totalLag
	topicLag.MaxLag = maxLag
	topicLag.TotalLogSize = totalLogSize
	if minLag == math.MaxInt64 {
		minLag = 0
	}
	topicLag.MinLag = minLag
	if len(partitionMap) > 0 {
		topicLag.AvgLag = float64(totalLag) / float64(len(partitionMap))
		topicLag.AvgLogSize = float64(totalLogSize) / float64(len(partitionMap))
	}

	if topicLag.AvgLogSize > 0 && totalLag > 0 {
		totalMsgSize := 0.0
		for _, p := range topicLag.Partitions {
			totalMsgSize += p.AvgMessageSize
		}
		topicLag.AvgMessageSize = totalMsgSize / float64(len(partitionMap))
	}

	topicLag.HotPartitions = a.findHotPartitions(topicLag, lagValues)
	topicLag.Status = a.determineTopicStatus(topicLag)

	return topicLag
}

func (a *lagAnalyzer) findHotPartitions(topicLag *TopicLag, lagValues []int64) []int32 {
	if len(lagValues) == 0 {
		return nil
	}

	mean := float64(0)
	for _, v := range lagValues {
		mean += float64(v)
	}
	mean /= float64(len(lagValues))

	variance := float64(0)
	for _, v := range lagValues {
		diff := float64(v) - mean
		variance += diff * diff
	}
	variance /= float64(len(lagValues))
	stdDev := math.Sqrt(variance)

	threshold := mean + (stdDev * a.cfg.HotspotThreshold)

	var hotPartitions []int32
	for _, p := range topicLag.Partitions {
		if float64(p.Lag) > threshold && p.Lag > a.cfg.LagThreshold {
			hotPartitions = append(hotPartitions, p.Partition)
		}
	}

	sort.Slice(hotPartitions, func(i, j int) bool {
		return hotPartitions[i] < hotPartitions[j]
	})

	return hotPartitions
}

func (a *lagAnalyzer) buildMemberPartitionMap(groupInfo *kafka.ConsumerGroupInfo) map[string]map[string][]int32 {
	result := make(map[string]map[string][]int32)
	for _, member := range groupInfo.Members {
		result[member.ClientID] = member.Partitions
	}
	return result
}

func (a *lagAnalyzer) findMemberForPartition(topic string, partition int32, memberPartitions map[string]map[string][]int32) string {
	for memberID, topics := range memberPartitions {
		if partitions, ok := topics[topic]; ok {
			for _, p := range partitions {
				if p == partition {
					return memberID
				}
			}
		}
	}
	return ""
}

func (a *lagAnalyzer) determineTopicStatus(topicLag *TopicLag) LagStatus {
	if topicLag.TotalLag == 0 {
		return StatusNormal
	}

	criticalCount := 0
	warningCount := 0
	for _, p := range topicLag.Partitions {
		switch p.Status {
		case StatusCritical:
			criticalCount++
		case StatusWarning:
			warningCount++
		}
	}

	if criticalCount > 0 {
		return StatusCritical
	}
	if warningCount > 0 {
		return StatusWarning
	}
	return StatusNormal
}

func (a *lagAnalyzer) determineOverallStatus(analysis *ConsumerGroupAnalysis) LagStatus {
	if len(analysis.Topics) == 0 {
		return StatusNormal
	}

	hasCritical := false
	hasWarning := false

	for _, t := range analysis.Topics {
		switch t.Status {
		case StatusCritical:
			hasCritical = true
		case StatusWarning:
			hasWarning = true
		}
	}

	if hasCritical {
		return StatusCritical
	}
	if hasWarning {
		return StatusWarning
	}
	return StatusNormal
}

func (a *lagAnalyzer) cfgTopics() []string {
	return nil
}

func (a *lagAnalyzer) getHistory(groupID, topic string, partition int32) []HistoricalLag {
	a.mu.RLock()
	defer a.mu.RUnlock()

	if _, ok := a.history[groupID]; !ok {
		return nil
	}
	if _, ok := a.history[groupID][topic]; !ok {
		return nil
	}
	return a.history[groupID][topic][partition]
}

func (a *lagAnalyzer) updateHistory(groupID, topic string, partition int32, entry HistoricalLag) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if _, ok := a.history[groupID]; !ok {
		a.history[groupID] = make(map[string]map[int32][]HistoricalLag)
	}
	if _, ok := a.history[groupID][topic]; !ok {
		a.history[groupID][topic] = make(map[int32][]HistoricalLag)
	}

	a.history[groupID][topic][partition] = append(a.history[groupID][topic][partition], entry)
	if len(a.history[groupID][topic][partition]) > a.cfg.HistoryRetention {
		a.history[groupID][topic][partition] = a.history[groupID][topic][partition][1:]
	}
}

func (a *lagAnalyzer) GetPartitionHistory(groupID, topic string, partition int32) []HistoricalLag {
	return a.getHistory(groupID, topic, partition)
}

func (a *lagAnalyzer) GetLatestAnalysis() []*ConsumerGroupAnalysis {
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.latest
}

func (a *lagAnalyzer) PredictProgress(groupID string) (*GroupProgressPrediction, error) {
	analysis := a.findGroupAnalysis(groupID)
	if analysis == nil {
		return nil, fmt.Errorf("consumer group %s not found", groupID)
	}

	return a.predictor.PredictGroupProgress(groupID, analysis, a.getHistory)
}

func (a *lagAnalyzer) SimulateConsumerAddition(groupID string, additionalConsumers int) (*ConsumerSimulation, error) {
	analysis := a.findGroupAnalysis(groupID)
	if analysis == nil {
		return nil, fmt.Errorf("consumer group %s not found", groupID)
	}

	return a.simulator.SimulateConsumerAddition(
		groupID,
		additionalConsumers,
		analysis,
		func(gid string) (*GroupProgressPrediction, error) {
			return a.PredictProgress(gid)
		},
	)
}

func (a *lagAnalyzer) GenerateRebalancePlan(groupID string) (*RebalancePlan, error) {
	analysis := a.findGroupAnalysis(groupID)
	if analysis == nil {
		return nil, fmt.Errorf("consumer group %s not found", groupID)
	}

	return a.simulator.GenerateRebalancePlan(groupID, analysis)
}

func (a *lagAnalyzer) findGroupAnalysis(groupID string) *ConsumerGroupAnalysis {
	a.mu.RLock()
	defer a.mu.RUnlock()

	for _, analysis := range a.latest {
		if analysis.GroupID == groupID {
			return analysis
		}
	}
	return nil
}

package analyzer

import (
	"fmt"
	"math"
	"time"

	"kafka-lag-analyzer/internal/prober"
)

func (a *lagAnalyzer) attributeDelays(analysis *ConsumerGroupAnalysis) []DelayAttribution {
	var attributions []DelayAttribution

	if slowAttr := a.detectSlowProcessing(analysis); slowAttr != nil {
		attributions = append(attributions, *slowAttr)
	}

	if networkAttr := a.detectNetworkLatencyRTT(analysis); networkAttr != nil {
		attributions = append(attributions, *networkAttr)
	}

	if imbalanceAttr := a.detectPartitionImbalance(analysis); imbalanceAttr != nil {
		attributions = append(attributions, *imbalanceAttr)
	}

	if rebalanceAttr := a.detectRebalancing(analysis); rebalanceAttr != nil {
		attributions = append(attributions, *rebalanceAttr)
	}

	if throughputAttr := a.detectHighThroughput(analysis); throughputAttr != nil {
		attributions = append(attributions, *throughputAttr)
	}

	return attributions
}

func (a *lagAnalyzer) detectSlowProcessing(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	var affectedTopics []string
	var affectedPartitions []string
	totalSlowPartitions := 0
	totalPartitions := 0

	for topic, topicLag := range analysis.Topics {
		topicSlow := 0
		for _, p := range topicLag.Partitions {
			totalPartitions++
			history := a.getHistory(analysis.GroupID, topic, p.Partition)
			if len(history) < 3 {
				continue
			}

			lagIncreasing := true
			offsetProgressing := true

			for i := 1; i < len(history); i++ {
				if history[i].Lag < history[i-1].Lag {
					lagIncreasing = false
				}
				if history[i].Offset <= history[i-1].Offset {
					offsetProgressing = false
				}
			}

			avgOffsetRate := 0.0
			if len(history) > 1 {
				offsetDiff := float64(history[len(history)-1].Offset - history[0].Offset)
				timeDiff := history[len(history)-1].Timestamp.Sub(history[0].Timestamp).Seconds()
				if timeDiff > 0 {
					avgOffsetRate = offsetDiff / timeDiff
				}
			}

			if lagIncreasing && offsetProgressing && avgOffsetRate < a.cfg.SlowProcessingThreshold {
				topicSlow++
				totalSlowPartitions++
				affectedPartitions = append(affectedPartitions, fmt.Sprintf("%s-%d", topic, p.Partition))
			}
		}

		if topicSlow > 0 {
			affectedTopics = append(affectedTopics, topic)
		}
	}

	if totalSlowPartitions == 0 {
		return nil
	}

	confidence := float64(totalSlowPartitions) / float64(math.Max(1, float64(totalPartitions)))
	severity := StatusNormal
	if confidence > 0.5 {
		severity = StatusCritical
	} else if confidence > 0.2 {
		severity = StatusWarning
	}

	return &DelayAttribution{
		Cause:              CauseSlowProcessing,
		Severity:           severity,
		Confidence:         confidence,
		Description:        fmt.Sprintf("检测到慢处理问题，%d/%d个分区消费速度低于阈值(%.2f msgs/sec)", totalSlowPartitions, totalPartitions, a.cfg.SlowProcessingThreshold),
		AffectedTopics:     affectedTopics,
		AffectedPartitions: affectedPartitions,
		Metrics: map[string]float64{
			"slow_partition_ratio": confidence,
			"avg_offset_rate":      a.calcAvgOffsetRate(analysis),
		},
	}
}

func (a *lagAnalyzer) detectNetworkLatencyRTT(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	if a.prober == nil {
		return a.detectNetworkLatencyFallback(analysis)
	}

	probeResult := a.prober.GetLatestResult()
	if probeResult == nil {
		return nil
	}

	summary := &NetworkRTTSummary{
		BrokerCount: len(probeResult.BrokerRTTs),
		BrokerRTTs:  make(map[int32]BrokerRTTInfo),
	}

	warningThreshold := time.Duration(a.kafkaCfg.RTTWarningThreshold) * time.Millisecond
	criticalThreshold := time.Duration(a.kafkaCfg.RTTCriticalThreshold) * time.Millisecond

	var affectedPartitions []string
	var affectedTopics []string
	highRTTCount := 0

	for id, brtt := range probeResult.BrokerRTTs {
		summary.BrokerRTTs[id] = BrokerRTTInfo{
			BrokerID: brtt.BrokerID,
			Host:     brtt.Host,
			RTT:      brtt.RTT,
			MinRTT:   brtt.MinRTT,
			MaxRTT:   brtt.MaxRTT,
			Jitter:   brtt.Jitter,
		}
		if brtt.Success && brtt.RTT > warningThreshold {
			highRTTCount++
		}
	}
	summary.OverallAvgRTT = probeResult.OverallAvgRTT
	summary.OverallMaxRTT = probeResult.OverallMaxRTT
	summary.HighRTTCount = highRTTCount

	analysis.NetworkRTTSummary = summary

	for topic, topicLag := range analysis.Topics {
		topicAffected := false
		for _, p := range topicLag.Partitions {
			if prtt, ok := probeResult.PartitionRTTs[topic]; ok {
				if partRTT, ok2 := prtt[p.Partition]; ok2 && partRTT.RTT > warningThreshold {
					affectedPartitions = append(affectedPartitions, fmt.Sprintf("%s-%d(%.1fms)", topic, p.Partition, float64(partRTT.RTT.Microseconds())/1000.0))
					topicAffected = true
				}
			}
		}
		if topicAffected {
			affectedTopics = append(affectedTopics, topic)
		}
	}

	if highRTTCount == 0 && len(affectedPartitions) == 0 {
		return nil
	}

	severity := StatusNormal
	confidence := float64(highRTTCount) / float64(math.Max(1, float64(len(probeResult.BrokerRTTs))))

	if probeResult.OverallMaxRTT > criticalThreshold {
		severity = StatusCritical
		confidence = math.Min(1.0, confidence*1.5)
	} else if probeResult.OverallMaxRTT > warningThreshold {
		severity = StatusWarning
	}

	return &DelayAttribution{
		Cause:              CauseNetworkLatency,
		Severity:           severity,
		Confidence:         confidence,
		Description:        fmt.Sprintf("主动RTT探测发现网络延迟问题，%d/%d个broker超过阈值(%.0fms)，平均RTT=%.1fms，最大RTT=%.1fms", highRTTCount, len(probeResult.BrokerRTTs), float64(warningThreshold.Milliseconds()), float64(probeResult.OverallAvgRTT.Microseconds())/1000.0, float64(probeResult.OverallMaxRTT.Microseconds())/1000.0),
		AffectedTopics:     affectedTopics,
		AffectedPartitions: affectedPartitions,
		Metrics: map[string]float64{
			"avg_rtt_ms":  float64(probeResult.OverallAvgRTT.Microseconds()) / 1000.0,
			"max_rtt_ms":  float64(probeResult.OverallMaxRTT.Microseconds()) / 1000.0,
			"jitter_ms":   a.calcAvgJitter(probeResult),
			"high_rtt_ratio": confidence,
		},
	}
}

func (a *lagAnalyzer) detectNetworkLatencyFallback(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	var affectedTopics []string
	var affectedPartitions []string
	totalNetworkPartitions := 0
	totalPartitions := 0

	for topic, topicLag := range analysis.Topics {
		topicNetwork := 0
		for _, p := range topicLag.Partitions {
			totalPartitions++
			history := a.getHistory(analysis.GroupID, topic, p.Partition)
			if len(history) < 5 {
				continue
			}

			lagVariance := float64(0)
			lagMean := float64(0)
			for _, h := range history {
				lagMean += float64(h.Lag)
			}
			lagMean /= float64(len(history))

			for _, h := range history {
				diff := float64(h.Lag) - lagMean
				lagVariance += diff * diff
			}
			lagVariance /= float64(len(history))
			lagStdDev := math.Sqrt(lagVariance)

			coeffVariation := 0.0
			if lagMean > 0 {
				coeffVariation = lagStdDev / lagMean
			}

			if coeffVariation > a.cfg.NetworkLatencyThreshold/1000 {
				topicNetwork++
				totalNetworkPartitions++
				affectedPartitions = append(affectedPartitions, fmt.Sprintf("%s-%d", topic, p.Partition))
			}
		}

		if topicNetwork > 0 {
			affectedTopics = append(affectedTopics, topic)
		}
	}

	if totalNetworkPartitions == 0 {
		return nil
	}

	confidence := float64(totalNetworkPartitions) / float64(math.Max(1, float64(totalPartitions)))
	severity := StatusNormal
	if confidence > 0.5 {
		severity = StatusCritical
	} else if confidence > 0.2 {
		severity = StatusWarning
	}

	return &DelayAttribution{
		Cause:              CauseNetworkLatency,
		Severity:           severity,
		Confidence:         confidence,
		Description:        fmt.Sprintf("检测到网络延迟问题(回退模式)，%d/%d个分区lag波动剧烈", totalNetworkPartitions, totalPartitions),
		AffectedTopics:     affectedTopics,
		AffectedPartitions: affectedPartitions,
		Metrics: map[string]float64{
			"high_variance_ratio": confidence,
			"method":             0,
		},
	}
}

func (a *lagAnalyzer) detectPartitionImbalance(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	var affectedTopics []string
	totalTopicsWithImbalance := 0
	allMetrics := make(map[string]float64)

	for topic, topicLag := range analysis.Topics {
		if topicLag.PartitionCount < 2 {
			continue
		}

		lagValues := make([]float64, 0, topicLag.PartitionCount)
		weights := make([]float64, 0, topicLag.PartitionCount)

		for _, p := range topicLag.Partitions {
			lagValues = append(lagValues, float64(p.Lag))

			weight := 1.0
			if p.AvgMessageSize > 0 && topicLag.AvgMessageSize > 0 {
				sizeRatio := p.AvgMessageSize / topicLag.AvgMessageSize
				weight = 1.0 + a.cfg.MessageSizeWeight*(sizeRatio-1.0)
				if weight < 0.1 {
					weight = 0.1
				}
			}
			if p.LogSize > 0 && topicLag.AvgLogSize > 0 {
				logRatio := float64(p.LogSize) / topicLag.AvgLogSize
				logWeight := 1.0 + a.cfg.MessageSizeWeight*(logRatio-1.0)
				if logWeight > weight {
					weight = logWeight
				}
			}
			weights = append(weights, weight)
		}

		weightedMean := 0.0
		totalWeight := 0.0
		for i, v := range lagValues {
			weightedMean += v * weights[i]
			totalWeight += weights[i]
		}
		if totalWeight == 0 {
			continue
		}
		weightedMean /= totalWeight

		if weightedMean == 0 {
			continue
		}

		weightedVariance := 0.0
		for i, v := range lagValues {
			diff := v - weightedMean
			weightedVariance += weights[i] * diff * diff
		}
		weightedVariance /= totalWeight
		weightedStdDev := math.Sqrt(weightedVariance)

		weightedImbalanceRatio := weightedStdDev / weightedMean

		allMetrics[fmt.Sprintf("%s_weighted_imbalance", topic)] = weightedImbalanceRatio
		allMetrics[fmt.Sprintf("%s_max_msg_size_bytes", topic)] = a.maxMsgSize(topicLag)

		if weightedImbalanceRatio > a.cfg.ImbalanceThreshold {
			totalTopicsWithImbalance++
			affectedTopics = append(affectedTopics, topic)
		}
	}

	if totalTopicsWithImbalance == 0 {
		return nil
	}

	confidence := float64(totalTopicsWithImbalance) / float64(math.Max(1, float64(len(analysis.Topics))))
	severity := StatusNormal
	if confidence > 0.5 {
		severity = StatusCritical
	} else if confidence > 0.2 {
		severity = StatusWarning
	}

	return &DelayAttribution{
		Cause:              CauseImbalance,
		Severity:           severity,
		Confidence:         confidence,
		Description:        fmt.Sprintf("检测到分区不均衡问题(含消息大小权重)，%d/%d个主题存在加权lag分布不均(>%.1f%%, 权重系数=%.2f)", totalTopicsWithImbalance, len(analysis.Topics), a.cfg.ImbalanceThreshold*100, a.cfg.MessageSizeWeight),
		AffectedTopics:     affectedTopics,
		AffectedPartitions: nil,
		Metrics:            allMetrics,
	}
}

func (a *lagAnalyzer) detectRebalancing(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	if analysis.State == "PreparingRebalance" || analysis.State == "CompletingRebalance" {
		return &DelayAttribution{
			Cause:              CauseRebalancing,
			Severity:           StatusWarning,
			Confidence:         1.0,
			Description:        fmt.Sprintf("消费组正在进行再平衡，当前状态: %s", analysis.State),
			AffectedTopics:     nil,
			AffectedPartitions: nil,
			Metrics:            map[string]float64{"is_rebalancing": 1},
		}
	}
	return nil
}

func (a *lagAnalyzer) detectHighThroughput(analysis *ConsumerGroupAnalysis) *DelayAttribution {
	var affectedTopics []string
	totalHighThroughput := 0
	totalTopics := 0

	for topic, topicLag := range analysis.Topics {
		totalTopics++

		throughputPerPartition := float64(0)
		if topicLag.PartitionCount > 0 {
			throughputPerPartition = float64(topicLag.TotalLag) / float64(topicLag.PartitionCount)
		}

		if throughputPerPartition > float64(a.cfg.LagThreshold) {
			totalHighThroughput++
			affectedTopics = append(affectedTopics, topic)
		}
	}

	if totalHighThroughput == 0 {
		return nil
	}

	confidence := float64(totalHighThroughput) / float64(math.Max(1, float64(totalTopics)))
	severity := StatusNormal
	if confidence > 0.5 {
		severity = StatusCritical
	} else if confidence > 0.2 {
		severity = StatusWarning
	}

	return &DelayAttribution{
		Cause:              CauseHighThroughput,
		Severity:           severity,
		Confidence:         confidence,
		Description:        fmt.Sprintf("检测到高吞吐量压力，%d/%d个主题消息流入速度超过消费能力", totalHighThroughput, totalTopics),
		AffectedTopics:     affectedTopics,
		AffectedPartitions: nil,
		Metrics: map[string]float64{
			"high_throughput_ratio": confidence,
		},
	}
}

func (a *lagAnalyzer) calcAvgOffsetRate(analysis *ConsumerGroupAnalysis) float64 {
	totalRate := 0.0
	count := 0
	for _, topicLag := range analysis.Topics {
		for _, p := range topicLag.Partitions {
			history := a.getHistory(analysis.GroupID, topicLag.Topic, p.Partition)
			if len(history) < 2 {
				continue
			}
			offsetDiff := float64(history[len(history)-1].Offset - history[0].Offset)
			timeDiff := history[len(history)-1].Timestamp.Sub(history[0].Timestamp).Seconds()
			if timeDiff > 0 {
				totalRate += offsetDiff / timeDiff
				count++
			}
		}
	}
	if count > 0 {
		return totalRate / float64(count)
	}
	return 0
}

func (a *lagAnalyzer) calcAvgJitter(result *prober.ProbeResult) float64 {
	totalJitter := 0.0
	count := 0
	for _, brtt := range result.BrokerRTTs {
		if brtt.Success && brtt.Jitter > 0 {
			totalJitter += float64(brtt.Jitter.Microseconds()) / 1000.0
			count++
		}
	}
	if count > 0 {
		return totalJitter / float64(count)
	}
	return 0
}

func (a *lagAnalyzer) maxMsgSize(topicLag *TopicLag) float64 {
	maxSize := 0.0
	for _, p := range topicLag.Partitions {
		if p.AvgMessageSize > maxSize {
			maxSize = p.AvgMessageSize
		}
	}
	return maxSize
}

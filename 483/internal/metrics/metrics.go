package metrics

import (
	"net/http"
	"strconv"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"kafka-lag-analyzer/internal/analyzer"
)

type Exporter interface {
	Handler() http.Handler
	Update(analyses []*analyzer.ConsumerGroupAnalysis)
	UpdatePredictions(predictions map[string]*analyzer.GroupProgressPrediction)
	UpdateSimulations(simulations map[string]*analyzer.ConsumerSimulation)
	UpdateRebalancePlans(plans map[string]*analyzer.RebalancePlan)
}

type prometheusExporter struct {
	partitionLag          *prometheus.GaugeVec
	partitionCurrentOffset *prometheus.GaugeVec
	partitionEndOffset    *prometheus.GaugeVec
	partitionLagChange    *prometheus.GaugeVec
	partitionLogSize      *prometheus.GaugeVec
	partitionAvgMsgSize   *prometheus.GaugeVec
	partitionBrokerRTT    *prometheus.GaugeVec
	topicTotalLag         *prometheus.GaugeVec
	topicAvgLag           *prometheus.GaugeVec
	topicMaxLag           *prometheus.GaugeVec
	topicMinLag           *prometheus.GaugeVec
	topicTotalLogSize     *prometheus.GaugeVec
	topicAvgMsgSize       *prometheus.GaugeVec
	groupTotalLag         *prometheus.GaugeVec
	groupMemberCount      *prometheus.GaugeVec
	groupStatus           *prometheus.GaugeVec
	partitionStatus       *prometheus.GaugeVec
	scrapeDuration        prometheus.Histogram
	delayCause            *prometheus.GaugeVec
	hotPartitionCount     *prometheus.GaugeVec
	brokerRTT             *prometheus.GaugeVec
	brokerJitter          *prometheus.GaugeVec
	networkAvgRTT         *prometheus.GaugeVec
	networkMaxRTT         *prometheus.GaugeVec
	predictedTimeToClear  *prometheus.GaugeVec
	predictedCatchup      *prometheus.GaugeVec
	consumptionRate       *prometheus.GaugeVec
	ingestionRate         *prometheus.GaugeVec
	simulatedImprovement  *prometheus.GaugeVec
	simulatedLagReduction *prometheus.GaugeVec
	rebalanceRecommended  *prometheus.GaugeVec
	rebalanceEstimatedGain *prometheus.GaugeVec
}

func NewExporter() Exporter {
	return &prometheusExporter{
		partitionLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_lag",
				Help:      "Current lag for a consumer group partition",
			},
			[]string{"group", "topic", "partition", "member"},
		),
		partitionCurrentOffset: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_current_offset",
				Help:      "Current committed offset for a consumer group partition",
			},
			[]string{"group", "topic", "partition"},
		),
		partitionEndOffset: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_end_offset",
				Help:      "Latest offset available in the partition",
			},
			[]string{"group", "topic", "partition"},
		),
		partitionLagChange: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_lag_change_rate",
				Help:      "Rate of change of lag for a partition",
			},
			[]string{"group", "topic", "partition"},
		),
		topicTotalLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_total_lag",
				Help:      "Total lag across all partitions for a topic",
			},
			[]string{"group", "topic"},
		),
		topicAvgLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_avg_lag",
				Help:      "Average lag across all partitions for a topic",
			},
			[]string{"group", "topic"},
		),
		topicMaxLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_max_lag",
				Help:      "Maximum lag across all partitions for a topic",
			},
			[]string{"group", "topic"},
		),
		topicMinLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_min_lag",
				Help:      "Minimum lag across all partitions for a topic",
			},
			[]string{"group", "topic"},
		),
		groupTotalLag: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "group_total_lag",
				Help:      "Total lag across all topics for a consumer group",
			},
			[]string{"group"},
		),
		groupMemberCount: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "group_member_count",
				Help:      "Number of members in the consumer group",
			},
			[]string{"group"},
		),
		groupStatus: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "group_status",
				Help:      "Status of the consumer group (0=normal, 1=warning, 2=critical)",
			},
			[]string{"group", "state"},
		),
		partitionStatus: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_status",
				Help:      "Status of the partition (0=normal, 1=warning, 2=critical)",
			},
			[]string{"group", "topic", "partition"},
		),
		scrapeDuration: promauto.NewHistogram(
			prometheus.HistogramOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "scrape_duration_seconds",
				Help:      "Duration of lag analysis scrape",
				Buckets:   []float64{0.1, 0.5, 1, 2, 5, 10},
			},
		),
		delayCause: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "delay_cause",
				Help:      "Detected delay cause with confidence level",
			},
			[]string{"group", "cause", "severity"},
		),
		hotPartitionCount: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "hot_partition_count",
				Help:      "Number of hot partitions for a consumer group",
			},
			[]string{"group"},
		),
		partitionLogSize: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_log_size_bytes",
				Help:      "Log size in bytes for a partition",
			},
			[]string{"group", "topic", "partition"},
		),
		partitionAvgMsgSize: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_avg_message_size_bytes",
				Help:      "Average message size in bytes for a partition",
			},
			[]string{"group", "topic", "partition"},
		),
		partitionBrokerRTT: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "partition_broker_rtt_ms",
				Help:      "RTT to the broker hosting this partition in milliseconds",
			},
			[]string{"group", "topic", "partition"},
		),
		topicTotalLogSize: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_total_log_size_bytes",
				Help:      "Total log size in bytes for a topic",
			},
			[]string{"group", "topic"},
		),
		topicAvgMsgSize: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "topic_avg_message_size_bytes",
				Help:      "Average message size in bytes for a topic",
			},
			[]string{"group", "topic"},
		),
		brokerRTT: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "broker_rtt_ms",
				Help:      "RTT to Kafka broker in milliseconds",
			},
			[]string{"broker_id", "host"},
		),
		brokerJitter: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "broker_jitter_ms",
				Help:      "Jitter (MaxRTT - MinRTT) to Kafka broker in milliseconds",
			},
			[]string{"broker_id", "host"},
		),
		networkAvgRTT: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "network_avg_rtt_ms",
				Help:      "Average RTT across all brokers for a consumer group",
			},
			[]string{"group"},
		),
		networkMaxRTT: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "network_max_rtt_ms",
				Help:      "Maximum RTT across all brokers for a consumer group",
			},
			[]string{"group"},
		),
		predictedTimeToClear: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "predicted_time_to_clear_seconds",
				Help:      "Predicted time in seconds to clear current lag",
			},
			[]string{"group", "topic", "partition"},
		),
		predictedCatchup: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "predicted_will_catch_up",
				Help:      "Whether the consumer is expected to catch up (1=yes, 0=no)",
			},
			[]string{"group", "topic", "partition"},
		),
		consumptionRate: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "consumption_rate_msgs_per_sec",
				Help:      "Current message consumption rate in messages per second",
			},
			[]string{"group", "topic", "partition"},
		),
		ingestionRate: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "ingestion_rate_msgs_per_sec",
				Help:      "Current message ingestion (production) rate in messages per second",
			},
			[]string{"group", "topic", "partition"},
		),
		simulatedImprovement: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "simulated_improvement_percent",
				Help:      "Simulated improvement percentage with additional consumers",
			},
			[]string{"group", "simulated_consumers"},
		),
		simulatedLagReduction: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "simulated_lag_reduction",
				Help:      "Simulated lag reduction in messages with additional consumers",
			},
			[]string{"group", "simulated_consumers"},
		),
		rebalanceRecommended: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "rebalance_recommended_partitions",
				Help:      "Number of partitions recommended for rebalance action",
			},
			[]string{"group", "action_type"},
		),
		rebalanceEstimatedGain: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Namespace: "kafka",
				Subsystem: "consumer_lag",
				Name:      "rebalance_estimated_gain_percent",
				Help:      "Estimated lag improvement percentage after rebalance",
			},
			[]string{"group"},
		),
	}
}

func (e *prometheusExporter) Handler() http.Handler {
	return promhttp.Handler()
}

func (e *prometheusExporter) Update(analyses []*analyzer.ConsumerGroupAnalysis) {
	e.partitionLag.Reset()
	e.partitionCurrentOffset.Reset()
	e.partitionEndOffset.Reset()
	e.partitionLagChange.Reset()
	e.partitionLogSize.Reset()
	e.partitionAvgMsgSize.Reset()
	e.partitionBrokerRTT.Reset()
	e.topicTotalLag.Reset()
	e.topicAvgLag.Reset()
	e.topicMaxLag.Reset()
	e.topicMinLag.Reset()
	e.topicTotalLogSize.Reset()
	e.topicAvgMsgSize.Reset()
	e.groupTotalLag.Reset()
	e.groupMemberCount.Reset()
	e.groupStatus.Reset()
	e.partitionStatus.Reset()
	e.delayCause.Reset()
	e.hotPartitionCount.Reset()
	e.brokerRTT.Reset()
	e.brokerJitter.Reset()
	e.networkAvgRTT.Reset()
	e.networkMaxRTT.Reset()
	e.predictedTimeToClear.Reset()
	e.predictedCatchup.Reset()
	e.consumptionRate.Reset()
	e.ingestionRate.Reset()
	e.simulatedImprovement.Reset()
	e.simulatedLagReduction.Reset()
	e.rebalanceRecommended.Reset()
	e.rebalanceEstimatedGain.Reset()

	for _, analysis := range analyses {
		e.groupTotalLag.WithLabelValues(analysis.GroupID).Set(float64(analysis.TotalLag))
		e.groupMemberCount.WithLabelValues(analysis.GroupID).Set(float64(analysis.MemberCount))

		statusValue := 0.0
		switch analysis.OverallStatus {
		case analyzer.StatusWarning:
			statusValue = 1
		case analyzer.StatusCritical:
			statusValue = 2
		}
		e.groupStatus.WithLabelValues(analysis.GroupID, analysis.State).Set(statusValue)

		e.hotPartitionCount.WithLabelValues(analysis.GroupID).Set(float64(len(analysis.HotPartitions)))

		if analysis.NetworkRTTSummary != nil {
			e.networkAvgRTT.WithLabelValues(analysis.GroupID).Set(float64(analysis.NetworkRTTSummary.OverallAvgRTT.Microseconds()) / 1000.0)
			e.networkMaxRTT.WithLabelValues(analysis.GroupID).Set(float64(analysis.NetworkRTTSummary.OverallMaxRTT.Microseconds()) / 1000.0)

			for _, brtt := range analysis.NetworkRTTSummary.BrokerRTTs {
				brokerIDStr := strconv.Itoa(int(brtt.BrokerID))
				e.brokerRTT.WithLabelValues(brokerIDStr, brtt.Host).Set(float64(brtt.RTT.Microseconds()) / 1000.0)
				e.brokerJitter.WithLabelValues(brokerIDStr, brtt.Host).Set(float64(brtt.Jitter.Microseconds()) / 1000.0)
			}
		}

		for _, attr := range analysis.DelayAttributions {
			severityValue := 0.0
			switch attr.Severity {
			case analyzer.StatusWarning:
				severityValue = 1
			case analyzer.StatusCritical:
				severityValue = 2
			}
			e.delayCause.WithLabelValues(
				analysis.GroupID,
				string(attr.Cause),
				string(attr.Severity),
			).Set(attr.Confidence * (severityValue + 1))
		}

		for topic, topicLag := range analysis.Topics {
			e.topicTotalLag.WithLabelValues(analysis.GroupID, topic).Set(float64(topicLag.TotalLag))
			e.topicAvgLag.WithLabelValues(analysis.GroupID, topic).Set(topicLag.AvgLag)
			e.topicMaxLag.WithLabelValues(analysis.GroupID, topic).Set(float64(topicLag.MaxLag))
			e.topicMinLag.WithLabelValues(analysis.GroupID, topic).Set(float64(topicLag.MinLag))
			e.topicTotalLogSize.WithLabelValues(analysis.GroupID, topic).Set(float64(topicLag.TotalLogSize))
			e.topicAvgMsgSize.WithLabelValues(analysis.GroupID, topic).Set(topicLag.AvgMessageSize)

			for _, p := range topicLag.Partitions {
				partitionStr := strconv.Itoa(int(p.Partition))
				e.partitionLag.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
					p.Member,
				).Set(float64(p.Lag))

				e.partitionCurrentOffset.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(float64(p.CurrentOffset))

				e.partitionEndOffset.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(float64(p.EndOffset))

				e.partitionLagChange.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(p.LagChangeRate)

				e.partitionLogSize.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(float64(p.LogSize))

				e.partitionAvgMsgSize.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(p.AvgMessageSize)

				if p.BrokerRTT > 0 {
					e.partitionBrokerRTT.WithLabelValues(
						analysis.GroupID,
						topic,
						partitionStr,
					).Set(float64(p.BrokerRTT.Microseconds()) / 1000.0)
				}

				pStatusValue := 0.0
				switch p.Status {
				case analyzer.StatusWarning:
					pStatusValue = 1
				case analyzer.StatusCritical:
					pStatusValue = 2
				}
				e.partitionStatus.WithLabelValues(
					analysis.GroupID,
					topic,
					partitionStr,
				).Set(pStatusValue)
			}
		}
	}
}

func (e *prometheusExporter) UpdatePredictions(predictions map[string]*analyzer.GroupProgressPrediction) {
	e.predictedTimeToClear.Reset()
	e.predictedCatchup.Reset()
	e.consumptionRate.Reset()
	e.ingestionRate.Reset()

	for groupID, prediction := range predictions {
		if prediction == nil {
			continue
		}

		for topic, partitions := range prediction.PartitionPredictions {
			for partition, partPred := range partitions {
				partitionStr := strconv.Itoa(int(partition))

				timeToClearSec := partPred.EstimatedTimeToClear.Seconds()
				if timeToClearSec > 0 && timeToClearSec < 1e18 {
					e.predictedTimeToClear.WithLabelValues(
						groupID, topic, partitionStr,
					).Set(timeToClearSec)
				}

				catchupValue := 0.0
				if partPred.WillCatchUp {
					catchupValue = 1.0
				}
				e.predictedCatchup.WithLabelValues(
					groupID, topic, partitionStr,
				).Set(catchupValue)

				e.consumptionRate.WithLabelValues(
					groupID, topic, partitionStr,
				).Set(partPred.ConsumptionRate)

				e.ingestionRate.WithLabelValues(
					groupID, topic, partitionStr,
				).Set(partPred.IngestionRate)
			}
		}
	}
}

func (e *prometheusExporter) UpdateSimulations(simulations map[string]*analyzer.ConsumerSimulation) {
	e.simulatedImprovement.Reset()
	e.simulatedLagReduction.Reset()

	for groupID, sim := range simulations {
		if sim == nil {
			continue
		}

		simConsumersStr := strconv.Itoa(sim.SimulatedMemberCount)
		lagReduction := float64(sim.OriginalTotalLag) - sim.SimulatedTotalLag
		if lagReduction < 0 {
			lagReduction = 0
		}

		e.simulatedImprovement.WithLabelValues(
			groupID, simConsumersStr,
		).Set(sim.ImprovementPercent)

		e.simulatedLagReduction.WithLabelValues(
			groupID, simConsumersStr,
		).Set(lagReduction)
	}
}

func (e *prometheusExporter) UpdateRebalancePlans(plans map[string]*analyzer.RebalancePlan) {
	e.rebalanceRecommended.Reset()
	e.rebalanceEstimatedGain.Reset()

	for groupID, plan := range plans {
		if plan == nil {
			continue
		}

		actionCounts := make(map[string]int)
		for _, action := range plan.HotPartitions {
			actionCounts[action.Action]++
		}

		for action, count := range actionCounts {
			e.rebalanceRecommended.WithLabelValues(
				groupID, action,
			).Set(float64(count))
		}

		e.rebalanceEstimatedGain.WithLabelValues(
			groupID,
		).Set(plan.EstimatedImprovement)
	}
}

package com.mqmonitor.comparison;

import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.ConsumerGroupComparison;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.util.StatsUtil;
import com.mqmonitor.common.util.TimeWindow;
import com.mqmonitor.collector.MetricsManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class ConsumerGroupComparator {
    private static final Logger logger = LoggerFactory.getLogger(ConsumerGroupComparator.class);

    private final MetricsManager metricsManager;

    public ConsumerGroupComparator() {
        this.metricsManager = MetricsManager.getInstance();
    }

    public ConsumerGroupComparison compareConsumerGroups(MQType mqType, String clusterName, String topic,
                                                         List<String> consumerGroups) {
        ConsumerGroupComparison comparison = new ConsumerGroupComparison();
        comparison.setMqType(mqType);
        comparison.setClusterName(clusterName);
        comparison.setTopic(topic);
        comparison.setConsumerGroups(consumerGroups);

        Map<String, ConsumerGroupComparison.GroupMetrics> groupMetricsMap = new HashMap<>();
        List<Long> allLags = new ArrayList<>();
        List<Double> allThroughputs = new ArrayList<>();
        List<Double> allLatencies = new ArrayList<>();
        List<Long> allP99Latencies = new ArrayList<>();
        List<Double> allLongTailRatios = new ArrayList<>();

        for (String group : consumerGroups) {
            ConsumerGroupComparison.GroupMetrics groupMetrics = calculateGroupMetrics(
                    mqType, clusterName, topic, group);
            groupMetricsMap.put(group, groupMetrics);

            allLags.add(groupMetrics.getCurrentLag());
            allThroughputs.add(groupMetrics.getThroughputMsgPerSec());
            allLatencies.add(groupMetrics.getAverageLatencyMs());
            allP99Latencies.add(groupMetrics.getP99LatencyMs());
            allLongTailRatios.add(groupMetrics.getLongTailRatio());
        }

        comparison.setGroupMetricsMap(groupMetricsMap);

        if (!groupMetricsMap.isEmpty()) {
            String bestGroup = Collections.max(groupMetricsMap.entrySet(),
                    Comparator.comparingDouble(e -> e.getValue().getHealthScore())).getKey();
            String worstGroup = Collections.min(groupMetricsMap.entrySet(),
                    Comparator.comparingDouble(e -> e.getValue().getHealthScore())).getKey();

            comparison.setBestPerformingGroup(bestGroup);
            comparison.setWorstPerformingGroup(worstGroup);

            comparison.setMaxLagDifference(Collections.max(allLags) - Collections.min(allLags));
            comparison.setMaxThroughputDifference(Collections.max(allThroughputs) - Collections.min(allThroughputs));
            comparison.setMaxLatencyDifference(Collections.max(allLatencies) - Collections.min(allLatencies));
            comparison.setMaxP99LatencyDifference(Collections.max(allP99Latencies) - Collections.min(allP99Latencies));
            comparison.setMaxLongTailRatioDifference(Collections.max(allLongTailRatios) - Collections.min(allLongTailRatios));
        }

        return comparison;
    }

    private ConsumerGroupComparison.GroupMetrics calculateGroupMetrics(MQType mqType, String clusterName,
                                                                       String topic, String consumerGroup) {
        ConsumerGroupComparison.GroupMetrics metrics = new ConsumerGroupComparison.GroupMetrics();
        metrics.setConsumerGroup(consumerGroup);

        List<QueueMetrics> latestMetrics = metricsManager.getMetrics(clusterName, topic, consumerGroup);

        if (latestMetrics != null && !latestMetrics.isEmpty()) {
            QueueMetrics latest = latestMetrics.get(latestMetrics.size() - 1);
            metrics.setCurrentLag(latest.getConsumerLag());
            metrics.setAverageLatencyMs(latest.getEndToEndLatencyMs());
            metrics.setP50LatencyMs(latest.getP50LatencyMs());
            metrics.setP95LatencyMs(latest.getP95LatencyMs());
            metrics.setP99LatencyMs(latest.getP99LatencyMs());

            if (latest.getP50LatencyMs() > 0) {
                metrics.setLongTailRatio((double) latest.getP99LatencyMs() / latest.getP50LatencyMs());
            }

            metrics.setThroughputMsgPerSec(latest.getConsumeThroughput());
            metrics.setConsumerCount(estimateConsumerCount(mqType, clusterName, topic, consumerGroup));

            String key = clusterName + ":" + topic + ":" + consumerGroup;
            TimeWindow<Double> lagWindow = metricsManager.getCollectorService().getBacklogHistoryMap().get(key);
            if (lagWindow != null && lagWindow.size() >= 5) {
                List<Double> lagValues = lagWindow.getValues();
                metrics.setLagTrend(StatsUtil.calculateGrowthRate(lagValues));
            }

            double healthScore = calculateHealthScore(metrics);
            metrics.setHealthScore(healthScore);
        }

        return metrics;
    }

    private int estimateConsumerCount(MQType mqType, String clusterName, String topic, String consumerGroup) {
        switch (mqType) {
            case KAFKA:
                try {
                    Set<String> groups = metricsManager.getCollectorService()
                            .getKafkaClients().get(clusterName).listConsumerGroups();
                    return groups.contains(consumerGroup) ? 3 : 1;
                } catch (Exception e) {
                    return 1;
                }
            default:
                return 1;
        }
    }

    private double calculateHealthScore(ConsumerGroupComparison.GroupMetrics metrics) {
        double score = 100.0;

        if (metrics.getCurrentLag() > 10000) {
            score -= 30;
        } else if (metrics.getCurrentLag() > 5000) {
            score -= 15;
        } else if (metrics.getCurrentLag() > 1000) {
            score -= 8;
        }

        if (metrics.getAverageLatencyMs() > 5000) {
            score -= 15;
        } else if (metrics.getAverageLatencyMs() > 1000) {
            score -= 8;
        } else if (metrics.getAverageLatencyMs() > 500) {
            score -= 3;
        }

        if (metrics.getP99LatencyMs() > 15000) {
            score -= 25;
        } else if (metrics.getP99LatencyMs() > 8000) {
            score -= 15;
        } else if (metrics.getP99LatencyMs() > 3000) {
            score -= 8;
        }

        if (metrics.getLongTailRatio() > 10) {
            score -= 20;
        } else if (metrics.getLongTailRatio() > 5) {
            score -= 12;
        } else if (metrics.getLongTailRatio() > 3) {
            score -= 5;
        }

        if (metrics.getThroughputMsgPerSec() < 10) {
            score -= 10;
        }

        if (metrics.getLagTrend() > 50) {
            score -= 15;
        } else if (metrics.getLagTrend() > 10) {
            score -= 8;
        }

        return Math.max(0, score);
    }

    public Map<String, Object> getComparisonSummary(ConsumerGroupComparison comparison) {
        Map<String, Object> summary = new LinkedHashMap<>();

        summary.put("topic", comparison.getTopic());
        summary.put("clusterName", comparison.getClusterName());
        summary.put("mqType", comparison.getMqType());
        summary.put("bestPerformingGroup", comparison.getBestPerformingGroup());
        summary.put("worstPerformingGroup", comparison.getWorstPerformingGroup());
        summary.put("maxLagDifference", comparison.getMaxLagDifference());
        summary.put("maxThroughputDifference", comparison.getMaxThroughputDifference());
        summary.put("maxLatencyDifference", comparison.getMaxLatencyDifference());
        summary.put("maxP99LatencyDifference", comparison.getMaxP99LatencyDifference());
        summary.put("maxLongTailRatioDifference", comparison.getMaxLongTailRatioDifference());

        List<Map<String, Object>> groupDetails = new ArrayList<>();
        for (Map.Entry<String, ConsumerGroupComparison.GroupMetrics> entry :
                comparison.getGroupMetricsMap().entrySet()) {
            Map<String, Object> detail = new LinkedHashMap<>();
            detail.put("consumerGroup", entry.getKey());
            detail.put("healthScore", entry.getValue().getHealthScore());
            detail.put("currentLag", entry.getValue().getCurrentLag());
            detail.put("averageLatencyMs", entry.getValue().getAverageLatencyMs());
            detail.put("p50LatencyMs", entry.getValue().getP50LatencyMs());
            detail.put("p95LatencyMs", entry.getValue().getP95LatencyMs());
            detail.put("p99LatencyMs", entry.getValue().getP99LatencyMs());
            detail.put("longTailRatio", entry.getValue().getLongTailRatio());
            detail.put("throughput", entry.getValue().getThroughputMsgPerSec());
            detail.put("consumerCount", entry.getValue().getConsumerCount());
            detail.put("lagTrend", entry.getValue().getLagTrend());
            groupDetails.add(detail);
        }

        groupDetails.sort((a, b) -> Double.compare(
                (Double) b.get("healthScore"), (Double) a.get("healthScore")));
        summary.put("groupDetails", groupDetails);

        return summary;
    }

    public List<ConsumerGroupComparison> compareAllTopics(MQType mqType, String clusterName) {
        List<ConsumerGroupComparison> comparisons = new ArrayList<>();

        List<QueueMetrics> allMetrics = metricsManager.getAllMetrics();
        Map<String, List<String>> topicGroups = allMetrics.stream()
                .filter(m -> m.getMqType() == mqType && m.getClusterName().equals(clusterName))
                .filter(m -> m.getConsumerGroup() != null)
                .collect(Collectors.groupingBy(
                        QueueMetrics::getTopic,
                        Collectors.mapping(QueueMetrics::getConsumerGroup, Collectors.toList())
                ));

        for (Map.Entry<String, List<String>> entry : topicGroups.entrySet()) {
            List<String> uniqueGroups = entry.getValue().stream().distinct().collect(Collectors.toList());
            if (uniqueGroups.size() >= 2) {
                ConsumerGroupComparison comparison = compareConsumerGroups(
                        mqType, clusterName, entry.getKey(), uniqueGroups);
                comparisons.add(comparison);
            }
        }

        return comparisons;
    }
}

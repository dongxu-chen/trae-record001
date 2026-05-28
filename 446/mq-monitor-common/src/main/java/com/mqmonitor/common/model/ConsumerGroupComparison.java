package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public class ConsumerGroupComparison {
    private MQType mqType;
    private String clusterName;
    private String topic;
    private long timestamp;
    private List<String> consumerGroups;
    private Map<String, GroupMetrics> groupMetricsMap;
    private String bestPerformingGroup;
    private String worstPerformingGroup;
    private double maxLagDifference;
    private double maxThroughputDifference;
    private double maxLatencyDifference;
    private long maxP99LatencyDifference;
    private double maxLongTailRatioDifference;

    public ConsumerGroupComparison() {
        this.timestamp = Instant.now().toEpochMilli();
    }

    public static class GroupMetrics {
        private String consumerGroup;
        private long currentLag;
        private double averageLatencyMs;
        private long p50LatencyMs;
        private long p95LatencyMs;
        private long p99LatencyMs;
        private double longTailRatio;
        private double throughputMsgPerSec;
        private int consumerCount;
        private double lagTrend;
        private double healthScore;

        public String getConsumerGroup() { return consumerGroup; }
        public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
        public long getCurrentLag() { return currentLag; }
        public void setCurrentLag(long currentLag) { this.currentLag = currentLag; }
        public double getAverageLatencyMs() { return averageLatencyMs; }
        public void setAverageLatencyMs(double averageLatencyMs) { this.averageLatencyMs = averageLatencyMs; }
        public long getP50LatencyMs() { return p50LatencyMs; }
        public void setP50LatencyMs(long p50LatencyMs) { this.p50LatencyMs = p50LatencyMs; }
        public long getP95LatencyMs() { return p95LatencyMs; }
        public void setP95LatencyMs(long p95LatencyMs) { this.p95LatencyMs = p95LatencyMs; }
        public long getP99LatencyMs() { return p99LatencyMs; }
        public void setP99LatencyMs(long p99LatencyMs) { this.p99LatencyMs = p99LatencyMs; }
        public double getLongTailRatio() { return longTailRatio; }
        public void setLongTailRatio(double longTailRatio) { this.longTailRatio = longTailRatio; }
        public double getThroughputMsgPerSec() { return throughputMsgPerSec; }
        public void setThroughputMsgPerSec(double throughputMsgPerSec) { this.throughputMsgPerSec = throughputMsgPerSec; }
        public int getConsumerCount() { return consumerCount; }
        public void setConsumerCount(int consumerCount) { this.consumerCount = consumerCount; }
        public double getLagTrend() { return lagTrend; }
        public void setLagTrend(double lagTrend) { this.lagTrend = lagTrend; }
        public double getHealthScore() { return healthScore; }
        public void setHealthScore(double healthScore) { this.healthScore = healthScore; }
    }

    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public List<String> getConsumerGroups() { return consumerGroups; }
    public void setConsumerGroups(List<String> consumerGroups) { this.consumerGroups = consumerGroups; }
    public Map<String, GroupMetrics> getGroupMetricsMap() { return groupMetricsMap; }
    public void setGroupMetricsMap(Map<String, GroupMetrics> groupMetricsMap) { this.groupMetricsMap = groupMetricsMap; }
    public String getBestPerformingGroup() { return bestPerformingGroup; }
    public void setBestPerformingGroup(String bestPerformingGroup) { this.bestPerformingGroup = bestPerformingGroup; }
    public String getWorstPerformingGroup() { return worstPerformingGroup; }
    public void setWorstPerformingGroup(String worstPerformingGroup) { this.worstPerformingGroup = worstPerformingGroup; }
    public double getMaxLagDifference() { return maxLagDifference; }
    public void setMaxLagDifference(double maxLagDifference) { this.maxLagDifference = maxLagDifference; }
    public double getMaxThroughputDifference() { return maxThroughputDifference; }
    public void setMaxThroughputDifference(double maxThroughputDifference) { this.maxThroughputDifference = maxThroughputDifference; }
    public double getMaxLatencyDifference() { return maxLatencyDifference; }
    public void setMaxLatencyDifference(double maxLatencyDifference) { this.maxLatencyDifference = maxLatencyDifference; }
    public long getMaxP99LatencyDifference() { return maxP99LatencyDifference; }
    public void setMaxP99LatencyDifference(long maxP99LatencyDifference) { this.maxP99LatencyDifference = maxP99LatencyDifference; }
    public double getMaxLongTailRatioDifference() { return maxLongTailRatioDifference; }
    public void setMaxLongTailRatioDifference(double maxLongTailRatioDifference) { this.maxLongTailRatioDifference = maxLongTailRatioDifference; }
}

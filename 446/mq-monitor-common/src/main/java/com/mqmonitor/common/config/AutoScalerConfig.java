package com.mqmonitor.common.config;

import com.mqmonitor.common.enums.MQType;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class AutoScalerConfig {
    public enum ScalingStrategy {
        LAG_THRESHOLD,
        LAG_RATE,
        PREDICTIVE,
        HYBRID
    }

    public enum ScalingAction {
        SCALE_UP,
        SCALE_DOWN,
        NO_CHANGE
    }

    private boolean enabled = true;
    private ScalingStrategy strategy = ScalingStrategy.HYBRID;
    private long checkIntervalMs = TimeUnit.SECONDS.toMillis(30);
    private long cooldownPeriodMs = TimeUnit.MINUTES.toMillis(5);
    private int minConsumers = 1;
    private int maxConsumers = 50;
    private int defaultScaleUpStep = 2;
    private int defaultScaleDownStep = 1;

    private long lagThreshold = 10000;
    private double lagRateThreshold = 1000.0;
    private long p99LatencyThresholdMs = 30000;
    private double longTailRatioThreshold = 5.0;

    private double scaleUpThreshold = 0.7;
    private double scaleDownThreshold = 0.3;

    private double predictiveWeight = 0.4;
    private int predictiveHorizonMinutes = 10;

    private boolean dryRun = false;
    private long maxScaleDownPerHour = 4;
    private long maxScaleUpPerHour = 8;

    private Map<String, GroupScalingConfig> groupConfigs = new HashMap<>();

    public static class GroupScalingConfig {
        private String consumerGroup;
        private String topic;
        private MQType mqType;
        private Integer minConsumers;
        private Integer maxConsumers;
        private Integer scaleUpStep;
        private Integer scaleDownStep;
        private Long lagThreshold;
        private Long p99LatencyThresholdMs;
        private Boolean enabled;

        public GroupScalingConfig() {}

        public GroupScalingConfig(String consumerGroup, String topic, MQType mqType) {
            this.consumerGroup = consumerGroup;
            this.topic = topic;
            this.mqType = mqType;
        }

        public int getEffectiveMinConsumers(AutoScalerConfig global) {
            return minConsumers != null ? minConsumers : global.getMinConsumers();
        }

        public int getEffectiveMaxConsumers(AutoScalerConfig global) {
            return maxConsumers != null ? maxConsumers : global.getMaxConsumers();
        }

        public int getEffectiveScaleUpStep(AutoScalerConfig global) {
            return scaleUpStep != null ? scaleUpStep : global.getDefaultScaleUpStep();
        }

        public int getEffectiveScaleDownStep(AutoScalerConfig global) {
            return scaleDownStep != null ? scaleDownStep : global.getDefaultScaleDownStep();
        }

        public long getEffectiveLagThreshold(AutoScalerConfig global) {
            return lagThreshold != null ? lagThreshold : global.getLagThreshold();
        }

        public long getEffectiveP99LatencyThreshold(AutoScalerConfig global) {
            return p99LatencyThresholdMs != null ? p99LatencyThresholdMs : global.getP99LatencyThresholdMs();
        }

        public boolean isEffectiveEnabled(AutoScalerConfig global) {
            return enabled != null ? enabled : global.isEnabled();
        }

        public String getConsumerGroup() { return consumerGroup; }
        public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
        public String getTopic() { return topic; }
        public void setTopic(String topic) { this.topic = topic; }
        public MQType getMqType() { return mqType; }
        public void setMqType(MQType mqType) { this.mqType = mqType; }
        public Integer getMinConsumers() { return minConsumers; }
        public void setMinConsumers(Integer minConsumers) { this.minConsumers = minConsumers; }
        public Integer getMaxConsumers() { return maxConsumers; }
        public void setMaxConsumers(Integer maxConsumers) { this.maxConsumers = maxConsumers; }
        public Integer getScaleUpStep() { return scaleUpStep; }
        public void setScaleUpStep(Integer scaleUpStep) { this.scaleUpStep = scaleUpStep; }
        public Integer getScaleDownStep() { return scaleDownStep; }
        public void setScaleDownStep(Integer scaleDownStep) { this.scaleDownStep = scaleDownStep; }
        public Long getLagThreshold() { return lagThreshold; }
        public void setLagThreshold(Long lagThreshold) { this.lagThreshold = lagThreshold; }
        public Long getP99LatencyThresholdMs() { return p99LatencyThresholdMs; }
        public void setP99LatencyThresholdMs(Long p99LatencyThresholdMs) { this.p99LatencyThresholdMs = p99LatencyThresholdMs; }
        public Boolean getEnabled() { return enabled; }
        public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    }

    public void addGroupConfig(GroupScalingConfig config) {
        String key = config.getMqType() + ":" + config.getTopic() + ":" + config.getConsumerGroup();
        groupConfigs.put(key, config);
    }

    public GroupScalingConfig getGroupConfig(MQType mqType, String topic, String consumerGroup) {
        String key = mqType + ":" + topic + ":" + consumerGroup;
        return groupConfigs.get(key);
    }

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public ScalingStrategy getStrategy() { return strategy; }
    public void setStrategy(ScalingStrategy strategy) { this.strategy = strategy; }
    public long getCheckIntervalMs() { return checkIntervalMs; }
    public void setCheckIntervalMs(long checkIntervalMs) { this.checkIntervalMs = checkIntervalMs; }
    public long getCooldownPeriodMs() { return cooldownPeriodMs; }
    public void setCooldownPeriodMs(long cooldownPeriodMs) { this.cooldownPeriodMs = cooldownPeriodMs; }
    public int getMinConsumers() { return minConsumers; }
    public void setMinConsumers(int minConsumers) { this.minConsumers = minConsumers; }
    public int getMaxConsumers() { return maxConsumers; }
    public void setMaxConsumers(int maxConsumers) { this.maxConsumers = maxConsumers; }
    public int getDefaultScaleUpStep() { return defaultScaleUpStep; }
    public void setDefaultScaleUpStep(int defaultScaleUpStep) { this.defaultScaleUpStep = defaultScaleUpStep; }
    public int getDefaultScaleDownStep() { return defaultScaleDownStep; }
    public void setDefaultScaleDownStep(int defaultScaleDownStep) { this.defaultScaleDownStep = defaultScaleDownStep; }
    public long getLagThreshold() { return lagThreshold; }
    public void setLagThreshold(long lagThreshold) { this.lagThreshold = lagThreshold; }
    public double getLagRateThreshold() { return lagRateThreshold; }
    public void setLagRateThreshold(double lagRateThreshold) { this.lagRateThreshold = lagRateThreshold; }
    public long getP99LatencyThresholdMs() { return p99LatencyThresholdMs; }
    public void setP99LatencyThresholdMs(long p99LatencyThresholdMs) { this.p99LatencyThresholdMs = p99LatencyThresholdMs; }
    public double getLongTailRatioThreshold() { return longTailRatioThreshold; }
    public void setLongTailRatioThreshold(double longTailRatioThreshold) { this.longTailRatioThreshold = longTailRatioThreshold; }
    public double getScaleUpThreshold() { return scaleUpThreshold; }
    public void setScaleUpThreshold(double scaleUpThreshold) { this.scaleUpThreshold = scaleUpThreshold; }
    public double getScaleDownThreshold() { return scaleDownThreshold; }
    public void setScaleDownThreshold(double scaleDownThreshold) { this.scaleDownThreshold = scaleDownThreshold; }
    public double getPredictiveWeight() { return predictiveWeight; }
    public void setPredictiveWeight(double predictiveWeight) { this.predictiveWeight = predictiveWeight; }
    public int getPredictiveHorizonMinutes() { return predictiveHorizonMinutes; }
    public void setPredictiveHorizonMinutes(int predictiveHorizonMinutes) { this.predictiveHorizonMinutes = predictiveHorizonMinutes; }
    public boolean isDryRun() { return dryRun; }
    public void setDryRun(boolean dryRun) { this.dryRun = dryRun; }
    public long getMaxScaleDownPerHour() { return maxScaleDownPerHour; }
    public void setMaxScaleDownPerHour(long maxScaleDownPerHour) { this.maxScaleDownPerHour = maxScaleDownPerHour; }
    public long getMaxScaleUpPerHour() { return maxScaleUpPerHour; }
    public void setMaxScaleUpPerHour(long maxScaleUpPerHour) { this.maxScaleUpPerHour = maxScaleUpPerHour; }
    public Map<String, GroupScalingConfig> getGroupConfigs() { return groupConfigs; }
    public void setGroupConfigs(Map<String, GroupScalingConfig> groupConfigs) { this.groupConfigs = groupConfigs; }
}

package com.mqmonitor.autoscaler;

import com.mqmonitor.common.config.AutoScalerConfig;
import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ScalingDecision {
    private AutoScalerConfig.ScalingAction action;
    private int currentConsumers;
    int targetConsumers;
    private int scaleAmount;
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String consumerGroup;
    private long timestamp;
    private String reason;
    private Map<String, Object> metrics = new LinkedHashMap<>();
    private Map<String, Object> factors = new LinkedHashMap<>();
    private boolean dryRun;
    private String strategy;
    private double confidence;
    private List<String> warnings = new ArrayList<>();

    public ScalingDecision() {
        this.timestamp = Instant.now().toEpochMilli();
        this.action = AutoScalerConfig.ScalingAction.NO_CHANGE;
    }

    public static ScalingDecision noChange(MQType mqType, String clusterName, String topic,
                                           String consumerGroup, int currentConsumers, String reason) {
        ScalingDecision decision = new ScalingDecision();
        decision.setMqType(mqType);
        decision.setClusterName(clusterName);
        decision.setTopic(topic);
        decision.setConsumerGroup(consumerGroup);
        decision.setCurrentConsumers(currentConsumers);
        decision.setTargetConsumers(currentConsumers);
        decision.setScaleAmount(0);
        decision.setAction(AutoScalerConfig.ScalingAction.NO_CHANGE);
        decision.setReason(reason);
        return decision;
    }

    public static ScalingDecision scaleUp(MQType mqType, String clusterName, String topic,
                                          String consumerGroup, int currentConsumers,
                                          int targetConsumers, String reason) {
        ScalingDecision decision = new ScalingDecision();
        decision.setMqType(mqType);
        decision.setClusterName(clusterName);
        decision.setTopic(topic);
        decision.setConsumerGroup(consumerGroup);
        decision.setCurrentConsumers(currentConsumers);
        decision.setTargetConsumers(targetConsumers);
        decision.setScaleAmount(targetConsumers - currentConsumers);
        decision.setAction(AutoScalerConfig.ScalingAction.SCALE_UP);
        decision.setReason(reason);
        return decision;
    }

    public static ScalingDecision scaleDown(MQType mqType, String clusterName, String topic,
                                            String consumerGroup, int currentConsumers,
                                            int targetConsumers, String reason) {
        ScalingDecision decision = new ScalingDecision();
        decision.setMqType(mqType);
        decision.setClusterName(clusterName);
        decision.setTopic(topic);
        decision.setConsumerGroup(consumerGroup);
        decision.setCurrentConsumers(currentConsumers);
        decision.setTargetConsumers(targetConsumers);
        decision.setScaleAmount(currentConsumers - targetConsumers);
        decision.setAction(AutoScalerConfig.ScalingAction.SCALE_DOWN);
        decision.setReason(reason);
        return decision;
    }

    public void addMetric(String name, Object value) {
        metrics.put(name, value);
    }

    public void addFactor(String name, Object value) {
        factors.put(name, value);
    }

    public void addWarning(String warning) {
        warnings.add(warning);
    }

    public Map<String, Object> toSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("timestamp", timestamp);
        summary.put("mqType", mqType);
        summary.put("clusterName", clusterName);
        summary.put("topic", topic);
        summary.put("consumerGroup", consumerGroup);
        summary.put("action", action);
        summary.put("currentConsumers", currentConsumers);
        summary.put("targetConsumers", targetConsumers);
        summary.put("scaleAmount", scaleAmount);
        summary.put("reason", reason);
        summary.put("strategy", strategy);
        summary.put("confidence", confidence);
        summary.put("dryRun", dryRun);
        summary.put("metrics", metrics);
        summary.put("factors", factors);
        if (!warnings.isEmpty()) {
            summary.put("warnings", warnings);
        }
        return summary;
    }

    public AutoScalerConfig.ScalingAction getAction() { return action; }
    public void setAction(AutoScalerConfig.ScalingAction action) { this.action = action; }
    public int getCurrentConsumers() { return currentConsumers; }
    public void setCurrentConsumers(int currentConsumers) { this.currentConsumers = currentConsumers; }
    public int getTargetConsumers() { return targetConsumers; }
    public void setTargetConsumers(int targetConsumers) { this.targetConsumers = targetConsumers; }
    public int getScaleAmount() { return scaleAmount; }
    public void setScaleAmount(int scaleAmount) { this.scaleAmount = scaleAmount; }
    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
    public Map<String, Object> getMetrics() { return metrics; }
    public void setMetrics(Map<String, Object> metrics) { this.metrics = metrics; }
    public Map<String, Object> getFactors() { return factors; }
    public void setFactors(Map<String, Object> factors) { this.factors = factors; }
    public boolean isDryRun() { return dryRun; }
    public void setDryRun(boolean dryRun) { this.dryRun = dryRun; }
    public String getStrategy() { return strategy; }
    public void setStrategy(String strategy) { this.strategy = strategy; }
    public double getConfidence() { return confidence; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public List<String> getWarnings() { return warnings; }
    public void setWarnings(List<String> warnings) { this.warnings = warnings; }
}

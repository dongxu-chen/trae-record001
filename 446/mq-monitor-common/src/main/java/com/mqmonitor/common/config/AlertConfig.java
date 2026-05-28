package com.mqmonitor.common.config;

import com.mqmonitor.common.enums.AlertLevel;

public class AlertConfig {
    private long latencyThresholdMs = 5000;
    private long p99LatencyThresholdMs = 15000;
    private double longTailRatioThreshold = 5.0;
    private long backlogThreshold = 10000;
    private double throughputDropThresholdPercent = 30.0;
    private long consumerLagThreshold = 5000;
    private double anomalyZScoreThreshold = 3.0;
    private AlertLevel defaultAlertLevel = AlertLevel.WARNING;
    private boolean webhookEnabled = false;
    private String webhookUrl;
    private int evaluationIntervalSeconds = 30;

    public long getLatencyThresholdMs() { return latencyThresholdMs; }
    public void setLatencyThresholdMs(long latencyThresholdMs) { this.latencyThresholdMs = latencyThresholdMs; }
    public long getP99LatencyThresholdMs() { return p99LatencyThresholdMs; }
    public void setP99LatencyThresholdMs(long p99LatencyThresholdMs) { this.p99LatencyThresholdMs = p99LatencyThresholdMs; }
    public double getLongTailRatioThreshold() { return longTailRatioThreshold; }
    public void setLongTailRatioThreshold(double longTailRatioThreshold) { this.longTailRatioThreshold = longTailRatioThreshold; }
    public long getBacklogThreshold() { return backlogThreshold; }
    public void setBacklogThreshold(long backlogThreshold) { this.backlogThreshold = backlogThreshold; }
    public double getThroughputDropThresholdPercent() { return throughputDropThresholdPercent; }
    public void setThroughputDropThresholdPercent(double throughputDropThresholdPercent) { this.throughputDropThresholdPercent = throughputDropThresholdPercent; }
    public long getConsumerLagThreshold() { return consumerLagThreshold; }
    public void setConsumerLagThreshold(long consumerLagThreshold) { this.consumerLagThreshold = consumerLagThreshold; }
    public double getAnomalyZScoreThreshold() { return anomalyZScoreThreshold; }
    public void setAnomalyZScoreThreshold(double anomalyZScoreThreshold) { this.anomalyZScoreThreshold = anomalyZScoreThreshold; }
    public AlertLevel getDefaultAlertLevel() { return defaultAlertLevel; }
    public void setDefaultAlertLevel(AlertLevel defaultAlertLevel) { this.defaultAlertLevel = defaultAlertLevel; }
    public boolean isWebhookEnabled() { return webhookEnabled; }
    public void setWebhookEnabled(boolean webhookEnabled) { this.webhookEnabled = webhookEnabled; }
    public String getWebhookUrl() { return webhookUrl; }
    public void setWebhookUrl(String webhookUrl) { this.webhookUrl = webhookUrl; }
    public int getEvaluationIntervalSeconds() { return evaluationIntervalSeconds; }
    public void setEvaluationIntervalSeconds(int evaluationIntervalSeconds) { this.evaluationIntervalSeconds = evaluationIntervalSeconds; }
}

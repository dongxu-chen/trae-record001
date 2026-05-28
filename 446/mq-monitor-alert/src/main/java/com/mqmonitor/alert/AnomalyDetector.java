package com.mqmonitor.alert;

import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.enums.AlertLevel;
import com.mqmonitor.common.enums.AlertType;
import com.mqmonitor.common.model.Alert;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.util.StatsUtil;
import com.mqmonitor.common.util.TimeWindow;
import com.mqmonitor.collector.MetricsManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

public class AnomalyDetector {
    private static final Logger logger = LoggerFactory.getLogger(AnomalyDetector.class);

    private final MetricsManager metricsManager;
    private final AlertConfig alertConfig;
    private final AlertNotifier alertNotifier;
    private final List<Alert> activeAlerts = new CopyOnWriteArrayList<>();
    private final Map<String, TimeWindow<Double>> latencyWindows = new ConcurrentHashMap<>();
    private final Map<String, TimeWindow<Double>> throughputWindows = new ConcurrentHashMap<>();
    private final long windowSizeMs = 3600000;

    public AnomalyDetector(AlertConfig alertConfig) {
        this.metricsManager = MetricsManager.getInstance();
        this.alertConfig = alertConfig;
        this.alertNotifier = new AlertNotifier(alertConfig);
    }

    public List<Alert> detectAnomalies(List<QueueMetrics> metricsList) {
        List<Alert> newAlerts = new ArrayList<>();

        for (QueueMetrics metrics : metricsList) {
            String key = buildKey(metrics);

            updateHistoryWindows(key, metrics);

            Alert latencyAlert = checkLatencyThreshold(key, metrics);
            if (latencyAlert != null) newAlerts.add(latencyAlert);

            Alert latencyAnomaly = checkLatencyAnomaly(key, metrics);
            if (latencyAnomaly != null) newAlerts.add(latencyAnomaly);

            Alert backlogAlert = checkBacklogThreshold(key, metrics);
            if (backlogAlert != null) newAlerts.add(backlogAlert);

            Alert backlogGrowth = checkBacklogGrowth(key, metrics);
            if (backlogGrowth != null) newAlerts.add(backlogGrowth);

            Alert throughputAlert = checkThroughputDrop(key, metrics);
            if (throughputAlert != null) newAlerts.add(throughputAlert);

            Alert lagAlert = checkConsumerLag(key, metrics);
            if (lagAlert != null) newAlerts.add(lagAlert);

            Alert p99Alert = checkP99LatencyThreshold(key, metrics);
            if (p99Alert != null) newAlerts.add(p99Alert);

            Alert longTailAlert = checkLongTailLatency(key, metrics);
            if (longTailAlert != null) newAlerts.add(longTailAlert);
        }

        for (Alert alert : newAlerts) {
            if (!isDuplicateAlert(alert)) {
                activeAlerts.add(alert);
                alertNotifier.sendAlert(alert);
            }
        }

        resolveRecoveredAlerts(metricsList);
        return newAlerts;
    }

    private String buildKey(QueueMetrics metrics) {
        return metrics.getMqType() + ":" + metrics.getClusterName() + ":" +
                metrics.getTopic() + (metrics.getConsumerGroup() != null ? ":" + metrics.getConsumerGroup() : "");
    }

    private void updateHistoryWindows(String key, QueueMetrics metrics) {
        getLatencyWindow(key).add((double) metrics.getEndToEndLatencyMs());
        getThroughputWindow(key).add(metrics.getConsumeThroughput());
    }

    private TimeWindow<Double> getLatencyWindow(String key) {
        return latencyWindows.computeIfAbsent(key, k -> new TimeWindow<>(windowSizeMs));
    }

    private TimeWindow<Double> getThroughputWindow(String key) {
        return throughputWindows.computeIfAbsent(key, k -> new TimeWindow<>(windowSizeMs));
    }

    private Alert checkLatencyThreshold(String key, QueueMetrics metrics) {
        if (metrics.getEndToEndLatencyMs() > alertConfig.getLatencyThresholdMs()) {
            return createAlert(AlertType.LATENCY_THRESHOLD,
                    AlertLevel.WARNING,
                    String.format("Latency %dms exceeds threshold %dms for %s",
                            metrics.getEndToEndLatencyMs(), alertConfig.getLatencyThresholdMs(), key),
                    metrics);
        }
        return null;
    }

    private Alert checkLatencyAnomaly(String key, QueueMetrics metrics) {
        TimeWindow<Double> window = getLatencyWindow(key);
        if (window.size() >= 10) {
            List<Double> history = window.getValues();
            double currentLatency = metrics.getEndToEndLatencyMs();

            if (StatsUtil.isAnomaly(currentLatency, history, alertConfig.getAnomalyZScoreThreshold())) {
                double zScore = StatsUtil.zScore(currentLatency, history);
                Map<String, Object> details = new HashMap<>();
                details.put("zScore", zScore);
                details.put("mean", StatsUtil.mean(history));
                details.put("stdDev", StatsUtil.standardDeviation(history));

                Alert alert = createAlert(AlertType.LATENCY_ANOMALY,
                        AlertLevel.ERROR,
                        String.format("Latency anomaly detected for %s: %.2fσ deviation", key, zScore),
                        metrics);
                alert.setDetails(details);
                return alert;
            }
        }
        return null;
    }

    private Alert checkBacklogThreshold(String key, QueueMetrics metrics) {
        if (metrics.getBacklogSize() > alertConfig.getBacklogThreshold()) {
            return createAlert(AlertType.BACKLOG_THRESHOLD,
                    AlertLevel.WARNING,
                    String.format("Backlog %d exceeds threshold %d for %s",
                            metrics.getBacklogSize(), alertConfig.getBacklogThreshold(), key),
                    metrics);
        }
        return null;
    }

    private Alert checkBacklogGrowth(String key, QueueMetrics metrics) {
        TimeWindow<Double> window = metricsManager.getCollectorService().getBacklogHistoryMap().get(key);
        if (window != null && window.size() >= 10) {
            List<Double> values = window.getValues();
            double growthRate = StatsUtil.calculateGrowthRate(values);
            if (growthRate > 100) {
                Map<String, Object> details = new HashMap<>();
                details.put("growthRate", growthRate);

                Alert alert = createAlert(AlertType.BACKLOG_GROWTH,
                        AlertLevel.WARNING,
                        String.format("Backlog growing rapidly for %s: %.2f msg/s", key, growthRate),
                        metrics);
                alert.setDetails(details);
                return alert;
            }
        }
        return null;
    }

    private Alert checkThroughputDrop(String key, QueueMetrics metrics) {
        TimeWindow<Double> window = getThroughputWindow(key);
        if (window != null && window.size() >= 5) {
            List<Double> values = window.getValues();
            double avgThroughput = StatsUtil.mean(values.subList(0, Math.max(0, values.size() - 1)));
            double currentThroughput = metrics.getConsumeThroughput();

            if (avgThroughput > 0) {
                double dropPercent = ((avgThroughput - currentThroughput) / avgThroughput) * 100;
                if (dropPercent > alertConfig.getThroughputDropThresholdPercent()) {
                    Map<String, Object> details = new HashMap<>();
                    details.put("dropPercent", dropPercent);
                    details.put("avgThroughput", avgThroughput);
                    details.put("currentThroughput", currentThroughput);

                    Alert alert = createAlert(AlertType.THROUGHPUT_DROP,
                            AlertLevel.WARNING,
                            String.format("Throughput dropped %.1f%% for %s", dropPercent, key),
                            metrics);
                    alert.setDetails(details);
                    return alert;
                }
            }
        }
        return null;
    }

    private Alert checkConsumerLag(String key, QueueMetrics metrics) {
        if (metrics.getConsumerLag() > alertConfig.getConsumerLagThreshold()) {
            AlertLevel level = metrics.getConsumerLag() > alertConfig.getConsumerLagThreshold() * 2
                    ? AlertLevel.CRITICAL : AlertLevel.ERROR;

            return createAlert(AlertType.CONSUMER_LAG,
                    level,
                    String.format("Consumer lag %d exceeds threshold %d for %s",
                            metrics.getConsumerLag(), alertConfig.getConsumerLagThreshold(), key),
                    metrics);
        }
        return null;
    }

    private Alert checkP99LatencyThreshold(String key, QueueMetrics metrics) {
        if (metrics.getP99LatencyMs() > 0) {
            long p99Threshold = alertConfig.getP99LatencyThresholdMs() > 0
                    ? alertConfig.getP99LatencyThresholdMs()
                    : alertConfig.getLatencyThresholdMs() * 3;

            if (metrics.getP99LatencyMs() > p99Threshold) {
                AlertLevel level = metrics.getP99LatencyMs() > p99Threshold * 2
                        ? AlertLevel.CRITICAL : AlertLevel.ERROR;

                Map<String, Object> details = new HashMap<>();
                details.put("p99Latency", metrics.getP99LatencyMs());
                details.put("p95Latency", metrics.getP95LatencyMs());
                details.put("p50Latency", metrics.getP50LatencyMs());
                details.put("avgLatency", metrics.getEndToEndLatencyMs());
                details.put("p99Threshold", p99Threshold);

                Alert alert = createAlert(AlertType.P99_LATENCY_THRESHOLD,
                        level,
                        String.format("P99 latency %dms exceeds threshold %dms for %s",
                                metrics.getP99LatencyMs(), p99Threshold, key),
                        metrics);
                alert.setDetails(details);
                return alert;
            }
        }
        return null;
    }

    private Alert checkLongTailLatency(String key, QueueMetrics metrics) {
        if (metrics.getP99LatencyMs() > 0 && metrics.getP50LatencyMs() > 0) {
            double tailRatio = (double) metrics.getP99LatencyMs() / metrics.getP50LatencyMs();
            double tailThreshold = alertConfig.getLongTailRatioThreshold() > 0
                    ? alertConfig.getLongTailRatioThreshold()
                    : 5.0;

            if (tailRatio > tailThreshold) {
                AlertLevel level = tailRatio > tailThreshold * 2
                        ? AlertLevel.ERROR : AlertLevel.WARNING;

                Map<String, Object> details = new HashMap<>();
                details.put("p99Latency", metrics.getP99LatencyMs());
                details.put("p50Latency", metrics.getP50LatencyMs());
                details.put("tailRatio", tailRatio);
                details.put("tailThreshold", tailThreshold);

                Alert alert = createAlert(AlertType.LONG_TAIL_LATENCY,
                        level,
                        String.format("Long tail latency detected for %s: P99/P50 ratio = %.2f (threshold: %.2f)",
                                key, tailRatio, tailThreshold),
                        metrics);
                alert.setDetails(details);
                return alert;
            }
        }
        return null;
    }

    private Alert createAlert(AlertType type, AlertLevel level, String message, QueueMetrics metrics) {
        Alert alert = new Alert(type, level, message);
        alert.setMqType(metrics.getMqType());
        alert.setClusterName(metrics.getClusterName());
        alert.setTopic(metrics.getTopic());
        alert.setConsumerGroup(metrics.getConsumerGroup());
        return alert;
    }

    private boolean isDuplicateAlert(Alert alert) {
        String key = alert.getType() + ":" + buildKeyFromAlert(alert);
        long now = System.currentTimeMillis();

        return activeAlerts.stream()
                .filter(a -> !a.isResolved())
                .anyMatch(a -> a.getType() == alert.getType()
                        && buildKeyFromAlert(a).equals(key)
                        && (now - a.getTimestamp()) < 60000);
    }

    private String buildKeyFromAlert(Alert alert) {
        return alert.getMqType() + ":" + alert.getClusterName() + ":" +
                alert.getTopic() + (alert.getConsumerGroup() != null ? ":" + alert.getConsumerGroup() : "");
    }

    private void resolveRecoveredAlerts(List<QueueMetrics> metricsList) {
        for (Alert alert : activeAlerts) {
            if (alert.isResolved()) continue;

            boolean recovered = metricsList.stream()
                    .filter(m -> m.getMqType() == alert.getMqType()
                            && m.getClusterName().equals(alert.getClusterName())
                            && m.getTopic().equals(alert.getTopic())
                            && Objects.equals(m.getConsumerGroup(), alert.getConsumerGroup()))
                    .allMatch(m -> isRecovered(alert, m));

            if (recovered) {
                alert.resolve();
                logger.info("Alert resolved: {} - {}", alert.getId(), alert.getMessage());
            }
        }
    }

    private boolean isRecovered(Alert alert, QueueMetrics metrics) {
        switch (alert.getType()) {
            case LATENCY_THRESHOLD:
                return metrics.getEndToEndLatencyMs() < alertConfig.getLatencyThresholdMs() * 0.8;
            case BACKLOG_THRESHOLD:
                return metrics.getBacklogSize() < alertConfig.getBacklogThreshold() * 0.8;
            case CONSUMER_LAG:
                return metrics.getConsumerLag() < alertConfig.getConsumerLagThreshold() * 0.8;
            default:
                return true;
        }
    }

    public List<Alert> getActiveAlerts() {
        List<Alert> result = new ArrayList<>();
        for (Alert alert : activeAlerts) {
            if (!alert.isResolved()) {
                result.add(alert);
            }
        }
        return result;
    }

    public List<Alert> getAllAlerts() {
        return new ArrayList<>(activeAlerts);
    }

    public AlertConfig getAlertConfig() {
        return alertConfig;
    }
}

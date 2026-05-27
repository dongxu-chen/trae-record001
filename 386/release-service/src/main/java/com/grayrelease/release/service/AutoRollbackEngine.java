package com.grayrelease.release.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.model.MetricThreshold;
import com.grayrelease.common.dto.MetricData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class AutoRollbackEngine {

    private final PrometheusMetricsService metricsService;
    private final ReleaseService releaseService;

    private final Map<String, MetricThreshold> monitoredReleases = new ConcurrentHashMap<>();
    private final Map<String, LocalDateTime> anomalyStartTimes = new ConcurrentHashMap<>();

    public void registerRelease(String releaseId, MetricThreshold threshold) {
        if (threshold != null) {
            monitoredReleases.put(releaseId, threshold);
            log.info("Auto-rollback monitor registered: releaseId={}, metric={}, threshold={}",
                    releaseId, threshold.getMetricType(), threshold.getCriticalThreshold());
        }
    }

    public void unregisterRelease(String releaseId) {
        monitoredReleases.remove(releaseId);
        anomalyStartTimes.remove(releaseId);
        log.info("Auto-rollback monitor unregistered: releaseId={}", releaseId);
    }

    @Scheduled(fixedRate = 10000)
    public void checkMetrics() {
        for (Map.Entry<String, MetricThreshold> entry : monitoredReleases.entrySet()) {
            String releaseId = entry.getKey();
            MetricThreshold threshold = entry.getValue();

            try {
                checkReleaseMetrics(releaseId, threshold);
            } catch (Exception e) {
                log.error("Error checking metrics for release: {}", releaseId, e);
            }
        }
    }

    private void checkReleaseMetrics(String releaseId, MetricThreshold threshold) {
        MetricData metricData = metricsService.getLatestMetric(releaseId, threshold.getMetricType());

        if (metricData == null) {
            return;
        }

        double value = metricData.getValue();
        double criticalThreshold = threshold.getCriticalThreshold();

        boolean isAbnormal = isValueAbnormal(value, criticalThreshold, threshold.getComparison());

        if (isAbnormal) {
            handleAnomaly(releaseId, threshold, metricData);
        } else {
            anomalyStartTimes.remove(releaseId);
        }
    }

    private boolean isValueAbnormal(double value, double threshold, String comparison) {
        if (comparison == null || "gt".equalsIgnoreCase(comparison)) {
            return value > threshold;
        } else if ("lt".equalsIgnoreCase(comparison)) {
            return value < threshold;
        }
        return value > threshold;
    }

    private void handleAnomaly(String releaseId, MetricThreshold threshold, MetricData metricData) {
        LocalDateTime firstDetected = anomalyStartTimes.get(releaseId);

        if (firstDetected == null) {
            firstDetected = LocalDateTime.now();
            anomalyStartTimes.put(releaseId, firstDetected);
            log.warn("Anomaly detected for release: {}, metric={}, value={}, threshold={}",
                    releaseId, threshold.getMetricType(), metricData.getValue(), threshold.getCriticalThreshold());
            return;
        }

        long durationSeconds = java.time.Duration.between(firstDetected, LocalDateTime.now()).getSeconds();

        if (durationSeconds >= threshold.getDurationSeconds()) {
            log.error("Auto-rollback triggered for release: {}, anomaly duration={}s exceeds threshold={}s",
                    releaseId, durationSeconds, threshold.getDurationSeconds());

            releaseService.rollbackRelease(releaseId,
                    "Auto-rollback: " + threshold.getMetricType() + "=" + metricData.getValue() +
                            " exceeded threshold " + threshold.getCriticalThreshold() +
                            " for " + durationSeconds + " seconds");
        }
    }
}
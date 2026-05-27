package com.grayrelease.monitor.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.model.MetricThreshold;
import com.grayrelease.common.dto.MetricData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnomalyDetectionService {

    private final PrometheusQueryService prometheusQueryService;
    private final DynamicBaselineAnalyzer dynamicBaselineAnalyzer;

    private final Map<String, LocalDateTime> anomalyStartTimes = new HashMap<>();

    @Value("${anomaly.detection.use-dynamic-baseline:true}")
    private boolean useDynamicBaseline;

    @Value("${anomaly.detection.std-dev-multiplier:3.0}")
    private double stdDevMultiplier;

    public MetricData checkMetric(String serviceName, String version, MetricType metricType, MetricThreshold threshold) {
        MetricData metricData = prometheusQueryService.queryMetric(serviceName, version, metricType);

        if (metricData == null) {
            return null;
        }

        boolean isAbnormal;
        double effectiveThreshold;

        if (useDynamicBaseline) {
            dynamicBaselineAnalyzer.recordDataPoint(serviceName, version, metricType, metricData.getValue());

            DynamicBaselineAnalyzer.BaselineResult baseline =
                    dynamicBaselineAnalyzer.calculateBaseline(serviceName, version, metricType);

            if (baseline.isAvailable()) {
                effectiveThreshold = baseline.getMean() + (stdDevMultiplier * baseline.getStandardDeviation());
                isAbnormal = metricData.getValue() > effectiveThreshold;
                log.debug("Dynamic baseline check: service={}, version={}, metric={}, value={}, " +
                                "mean={}, stdDev={}, threshold={}",
                        serviceName, version, metricType, metricData.getValue(),
                        baseline.getMean(), baseline.getStandardDeviation(), effectiveThreshold);
            } else {
                effectiveThreshold = threshold.getCriticalThreshold();
                isAbnormal = detectAnomaly(metricData.getValue(), threshold);
            }
        } else {
            effectiveThreshold = threshold.getCriticalThreshold();
            isAbnormal = detectAnomaly(metricData.getValue(), threshold);
        }

        metricData.setIsAbnormal(isAbnormal);
        metricData.setThreshold(effectiveThreshold);

        if (isAbnormal) {
            String key = serviceName + ":" + version + ":" + metricType;
            LocalDateTime firstDetected = anomalyStartTimes.get(key);

            if (firstDetected == null) {
                anomalyStartTimes.put(key, LocalDateTime.now());
                log.warn("Anomaly detected: service={}, version={}, metric={}, value={}, threshold={}, dynamic={}",
                        serviceName, version, metricType, metricData.getValue(), effectiveThreshold, useDynamicBaseline);
            } else {
                long durationSeconds = java.time.Duration.between(firstDetected, LocalDateTime.now()).getSeconds();
                if (durationSeconds >= threshold.getDurationSeconds()) {
                    log.error("Sustained anomaly: service={}, version={}, metric={}, duration={}s, value={}, threshold={}",
                            serviceName, version, metricType, durationSeconds, metricData.getValue(), effectiveThreshold);
                }
            }
        } else {
            String key = serviceName + ":" + version + ":" + metricType;
            anomalyStartTimes.remove(key);
        }

        return metricData;
    }

    public boolean detectAnomaly(double value, MetricThreshold threshold) {
        double criticalThreshold = threshold.getCriticalThreshold();
        String comparison = threshold.getComparison();

        if (comparison == null || "gt".equalsIgnoreCase(comparison)) {
            return value > criticalThreshold;
        } else if ("lt".equalsIgnoreCase(comparison)) {
            return value < criticalThreshold;
        }
        return value > criticalThreshold;
    }

    public AnomalyReport analyzeMetrics(String serviceName, String version,
                                         List<MetricThreshold> thresholds) {
        AnomalyReport report = new AnomalyReport();
        report.setServiceName(serviceName);
        report.setVersion(version);
        report.setAnalysisTime(LocalDateTime.now());

        for (MetricThreshold threshold : thresholds) {
            MetricData metricData = checkMetric(serviceName, version, threshold.getMetricType(), threshold);
            if (metricData != null && metricData.getIsAbnormal()) {
                report.addAnomaly(metricData);
            }
        }

        if (useDynamicBaseline) {
            Map<String, DynamicBaselineAnalyzer.BaselineResult> baselines =
                    dynamicBaselineAnalyzer.getAllBaselines(serviceName, version);
            report.setBaselines(baselines);
        }

        return report;
    }

    public DynamicBaselineAnalyzer.BaselineResult getBaseline(String serviceName, String version, MetricType metricType) {
        return dynamicBaselineAnalyzer.calculateBaseline(serviceName, version, metricType);
    }

    @lombok.Data
    public static class AnomalyReport {
        private String serviceName;
        private String version;
        private LocalDateTime analysisTime;
        private List<MetricData> anomalies = new java.util.ArrayList<>();
        private Map<String, DynamicBaselineAnalyzer.BaselineResult> baselines = new HashMap<>();

        public void addAnomaly(MetricData metricData) {
            anomalies.add(metricData);
        }

        public boolean hasAnomalies() {
            return !anomalies.isEmpty();
        }
    }
}
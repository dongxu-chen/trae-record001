package com.grayrelease.monitor.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.dto.MetricData;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class DynamicBaselineAnalyzer {

    private final Map<String, Deque<MetricDataPoint>> historyData = new ConcurrentHashMap<>();

    private static final int MAX_HISTORY_SIZE = 1000;

    private static final double DEFAULT_STD_DEV_MULTIPLIER = 3.0;

    private static final int MIN_DATA_POINTS = 10;

    public void recordDataPoint(String serviceName, String version, MetricType metricType, double value) {
        String key = buildKey(serviceName, version, metricType);

        historyData.computeIfAbsent(key, k -> new ArrayDeque<>());

        Deque<MetricDataPoint> deque = historyData.get(key);
        synchronized (deque) {
            deque.addLast(new MetricDataPoint(value, LocalDateTime.now()));
            while (deque.size() > MAX_HISTORY_SIZE) {
                deque.pollFirst();
            }
        }
    }

    public BaselineResult calculateBaseline(String serviceName, String version, MetricType metricType) {
        String key = buildKey(serviceName, version, metricType);
        Deque<MetricDataPoint> deque = historyData.get(key);

        if (deque == null || deque.size() < MIN_DATA_POINTS) {
            return BaselineResult.builder()
                    .available(false)
                    .message("Insufficient historical data: " + (deque != null ? deque.size() : 0) + " points")
                    .build();
        }

        List<Double> values;
        synchronized (deque) {
            values = deque.stream().map(MetricDataPoint::getValue).toList();
        }

        double mean = calculateMean(values);
        double stdDev = calculateStandardDeviation(values, mean);
        double dynamicThreshold = mean + (DEFAULT_STD_DEV_MULTIPLIER * stdDev);

        return BaselineResult.builder()
                .available(true)
                .mean(mean)
                .standardDeviation(stdDev)
                .dynamicThreshold(dynamicThreshold)
                .dataPoints(values.size())
                .min(Collections.min(values))
                .max(Collections.max(values))
                .percentile95(calculatePercentile(values, 95))
                .percentile99(calculatePercentile(values, 99))
                .build();
    }

    public boolean isAnomaly(String serviceName, String version, MetricType metricType,
                              double currentValue, double stdDevMultiplier) {
        BaselineResult baseline = calculateBaseline(serviceName, version, metricType);

        if (!baseline.isAvailable()) {
            return false;
        }

        double threshold = baseline.getMean() + (stdDevMultiplier * baseline.getStandardDeviation());
        boolean isAnomaly = currentValue > threshold;

        if (isAnomaly) {
            log.warn("Dynamic baseline anomaly detected: service={}, version={}, metric={}, " +
                            "value={}, mean={}, stdDev={}, threshold={}",
                    serviceName, version, metricType, currentValue,
                    baseline.getMean(), baseline.getStandardDeviation(), threshold);
        }

        return isAnomaly;
    }

    public BaselineResult getBaselineWithCustomMultiplier(String serviceName, String version,
                                                            MetricType metricType, double stdDevMultiplier) {
        BaselineResult baseline = calculateBaseline(serviceName, version, metricType);

        if (baseline.isAvailable()) {
            baseline.setDynamicThreshold(baseline.getMean() + (stdDevMultiplier * baseline.getStandardDeviation()));
        }

        return baseline;
    }

    public void clearHistory(String serviceName, String version, MetricType metricType) {
        String key = buildKey(serviceName, version, metricType);
        historyData.remove(key);
        log.info("Cleared baseline history: service={}, version={}, metric={}", serviceName, version, metricType);
    }

    public void clearAllHistory(String serviceName) {
        List<String> keysToRemove = historyData.keySet().stream()
                .filter(key -> key.startsWith(serviceName))
                .toList();
        keysToRemove.forEach(historyData::remove);
        log.info("Cleared all baseline history for service: {}", serviceName);
    }

    public Map<String, BaselineResult> getAllBaselines(String serviceName, String version) {
        Map<String, BaselineResult> baselines = new HashMap<>();

        for (MetricType metricType : MetricType.values()) {
            BaselineResult result = calculateBaseline(serviceName, version, metricType);
            baselines.put(metricType.name(), result);
        }

        return baselines;
    }

    private double calculateMean(List<Double> values) {
        return values.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
    }

    private double calculateStandardDeviation(List<Double> values, double mean) {
        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .average()
                .orElse(0.0);
        return Math.sqrt(variance);
    }

    private double calculatePercentile(List<Double> sortedValues, double percentile) {
        List<Double> sorted = new ArrayList<>(sortedValues);
        Collections.sort(sorted);

        int index = (int) Math.ceil(percentile / 100.0 * sorted.size());
        if (index == 0) index = 1;
        if (index > sorted.size()) index = sorted.size();

        return sorted.get(index - 1);
    }

    private String buildKey(String serviceName, String version, MetricType metricType) {
        return serviceName + ":" + version + ":" + metricType.name();
    }

    @Data
    public static class MetricDataPoint {
        private final double value;
        private final LocalDateTime timestamp;
    }

    @Data
    @lombok.Builder
    @lombok.AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class BaselineResult {
        private boolean available;
        private double mean;
        private double standardDeviation;
        private double dynamicThreshold;
        private int dataPoints;
        private double min;
        private double max;
        private double percentile95;
        private double percentile99;
        private String message;
    }
}
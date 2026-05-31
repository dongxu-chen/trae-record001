package com.oauth2.monitor.anomaly;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;

@Slf4j
@Service
public class BaselineLearningService {

    private final MeterRegistry meterRegistry;

    @Value("${oauth2.monitor.baseline.window-minutes:60}")
    private int baselineWindowMinutes;

    @Value("${oauth2.monitor.baseline.update-interval-seconds:60}")
    private int updateIntervalSeconds;

    @Value("${oauth2.monitor.baseline.min-samples:30}")
    private int minSamples;

    @Value("${oauth2.monitor.baseline.history-size:10080}")
    private int historySize;

    private final Map<String, LinkedList<Double>> metricHistory = new ConcurrentHashMap<>();
    private final Map<String, AtomicReference<MetricsBaseline>> baselines = new ConcurrentHashMap<>();
    private final Map<String, List<Double>> currentWindowSamples = new ConcurrentHashMap<>();

    private final Set<String> monitoredMetrics = ConcurrentHashMap.newKeySet();

    public BaselineLearningService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        initializeDefaultMetrics();
    }

    private void initializeDefaultMetrics() {
        monitoredMetrics.addAll(Arrays.asList(
                "token_request_rate",
                "authorization_code_request_rate",
                "token_failure_rate",
                "authorization_code_failure_rate",
                "token_issue_latency_p95",
                "authorization_code_latency_p95",
                "invalid_token_attempts_rate",
                "error_rate_invalid_client",
                "error_rate_invalid_grant",
                "error_rate_invalid_token"
        ));
    }

    public void registerMetric(String metricName) {
        monitoredMetrics.add(metricName);
        metricHistory.computeIfAbsent(metricName, k -> new LinkedList<>());
        currentWindowSamples.computeIfAbsent(metricName, k -> Collections.synchronizedList(new ArrayList<>()));
        baselines.computeIfAbsent(metricName, k -> new AtomicReference<>(MetricsBaseline.builder()
                .metricName(metricName)
                .initialized(false)
                .build()));
        log.info("Registered metric for baseline learning: {}", metricName);
    }

    public void recordSample(String metricName, double value) {
        if (!monitoredMetrics.contains(metricName)) {
            registerMetric(metricName);
        }

        currentWindowSamples.computeIfAbsent(metricName, k -> Collections.synchronizedList(new ArrayList<>()))
                .add(value);

        LinkedList<Double> history = metricHistory.computeIfAbsent(metricName, k -> new LinkedList<>());
        synchronized (history) {
            history.add(value);
            while (history.size() > historySize) {
                history.removeFirst();
            }
        }
    }

    @Scheduled(fixedDelayString = "${oauth2.monitor.baseline.update-interval-seconds:60}000")
    public void updateBaselines() {
        log.debug("Updating baselines for {} metrics", monitoredMetrics.size());

        for (String metricName : monitoredMetrics) {
            try {
                updateMetricBaseline(metricName);
            } catch (Exception e) {
                log.error("Failed to update baseline for metric: {}", metricName, e);
            }
        }
    }

    private void updateMetricBaseline(String metricName) {
        List<Double> samples = currentWindowSamples.get(metricName);
        if (samples == null || samples.isEmpty()) {
            return;
        }

        List<Double> windowSamples;
        synchronized (samples) {
            windowSamples = new ArrayList<>(samples);
            samples.clear();
        }

        if (windowSamples.size() < minSamples) {
            log.debug("Not enough samples for {}: {}/{}", metricName, windowSamples.size(), minSamples);
            return;
        }

        double[] sampleArray = windowSamples.stream().mapToDouble(Double::doubleValue).toArray();
        MetricsBaseline newBaseline = MetricsBaseline.fromSamples(sampleArray);
        newBaseline.setMetricName(metricName);
        newBaseline.setWindowStart(Instant.now().minus(Duration.ofSeconds(updateIntervalSeconds)));
        newBaseline.setWindowEnd(Instant.now());
        newBaseline.setWindowSize(Duration.ofSeconds(updateIntervalSeconds));

        AtomicReference<MetricsBaseline> baselineRef = baselines.computeIfAbsent(
                metricName, k -> new AtomicReference<>());
        MetricsBaseline oldBaseline = baselineRef.getAndSet(newBaseline);

        if (oldBaseline == null || !oldBaseline.isInitialized()) {
            log.info("Initialized baseline for {}: mean={}, sigma={}, samples={}",
                    metricName, String.format("%.2f", newBaseline.getMean()),
                    String.format("%.2f", newBaseline.getStandardDeviation()),
                    newBaseline.getSampleCount());
        } else {
            double meanChange = Math.abs(newBaseline.getMean() - oldBaseline.getMean()) /
                    (oldBaseline.getMean() + 0.0001) * 100;
            if (meanChange > 10) {
                log.info("Baseline updated for {}: mean={} (Δ{}%), sigma={}, samples={}",
                        metricName, String.format("%.2f", newBaseline.getMean()),
                        String.format("%.1f", meanChange),
                        String.format("%.2f", newBaseline.getStandardDeviation()),
                        newBaseline.getSampleCount());
            }
        }
    }

    public MetricsBaseline getBaseline(String metricName) {
        AtomicReference<MetricsBaseline> baselineRef = baselines.get(metricName);
        if (baselineRef == null) {
            return MetricsBaseline.builder()
                    .metricName(metricName)
                    .initialized(false)
                    .build();
        }
        return baselineRef.get();
    }

    public MetricsBaseline.AnomalyLevel checkAnomaly(String metricName, double value) {
        MetricsBaseline baseline = getBaseline(metricName);
        return baseline.checkAnomaly(value);
    }

    public AnomalyResult analyzeAnomaly(String metricName, double value) {
        MetricsBaseline baseline = getBaseline(metricName);
        MetricsBaseline.AnomalyLevel level = baseline.checkAnomaly(value);
        double zScore = baseline.calculateZScore(value);
        double deviation = baseline.getDeviationPercentage(value);

        return AnomalyResult.builder()
                .metricName(metricName)
                .value(value)
                .anomalyLevel(level)
                .zScore(zScore)
                .deviationPercentage(deviation)
                .baseline(baseline)
                .description(baseline.getAnomalyDescription(value))
                .timestamp(Instant.now())
                .build();
    }

    public List<AnomalyResult> scanForAnomalies(Map<String, Double> currentValues) {
        List<AnomalyResult> anomalies = new ArrayList<>();

        for (Map.Entry<String, Double> entry : currentValues.entrySet()) {
            String metricName = entry.getKey();
            Double value = entry.getValue();

            if (monitoredMetrics.contains(metricName)) {
                AnomalyResult result = analyzeAnomaly(metricName, value);
                if (result.getAnomalyLevel() != MetricsBaseline.AnomalyLevel.NORMAL) {
                    anomalies.add(result);
                    log.warn("Anomaly detected - {}: {}", metricName, result.getDescription());
                }
            }
        }

        return anomalies;
    }

    public Map<String, MetricsBaseline> getAllBaselines() {
        Map<String, MetricsBaseline> result = new HashMap<>();
        for (Map.Entry<String, AtomicReference<MetricsBaseline>> entry : baselines.entrySet()) {
            result.put(entry.getKey(), entry.getValue().get());
        }
        return result;
    }

    public List<String> getMonitoredMetrics() {
        return new ArrayList<>(monitoredMetrics);
    }

    public void triggerBaselineRecalculation(String metricName) {
        LinkedList<Double> history = metricHistory.get(metricName);
        if (history == null || history.size() < minSamples) {
            return;
        }

        synchronized (history) {
            double[] samples = history.stream().mapToDouble(Double::doubleValue).toArray();
            MetricsBaseline newBaseline = MetricsBaseline.fromSamples(samples);
            newBaseline.setMetricName(metricName);

            baselines.computeIfAbsent(metricName, k -> new AtomicReference<>())
                    .set(newBaseline);

            log.info("Manual baseline recalculation for {}: mean={}, sigma={}, samples={}",
                    metricName, String.format("%.2f", newBaseline.getMean()),
                    String.format("%.2f", newBaseline.getStandardDeviation()),
                    newBaseline.getSampleCount());
        }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AnomalyResult {
        private String metricName;
        private double value;
        private MetricsBaseline.AnomalyLevel anomalyLevel;
        private double zScore;
        private double deviationPercentage;
        private MetricsBaseline baseline;
        private String description;
        private Instant timestamp;

        public boolean isSignificant() {
            return anomalyLevel == MetricsBaseline.AnomalyLevel.CRITICAL ||
                    anomalyLevel == MetricsBaseline.AnomalyLevel.EXTREME;
        }
    }
}

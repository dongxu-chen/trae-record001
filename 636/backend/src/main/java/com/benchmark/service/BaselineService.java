package com.benchmark.service;

import com.benchmark.dto.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class BaselineService {

    private final Map<String, PerformanceBaseline> baselineStore = new ConcurrentHashMap<>();
    private final Map<String, List<BaselineComparison>> comparisonHistory = new ConcurrentHashMap<>();

    public PerformanceBaseline createBaseline(TestReport report) {
        PerformanceBaseline baseline = PerformanceBaseline.builder()
            .id(UUID.randomUUID().toString())
            .algorithm(report.getConfig().getAlgorithm())
            .threadCount(report.getConfig().getThreadCount())
            .createdTime(System.currentTimeMillis())
            .isBest(false)
            .avgQps(report.getSummary().getAvgQps())
            .peakQps(report.getSummary().getPeakQps())
            .avgLatency(report.getLatencyStats().getAvg())
            .p50Latency(report.getLatencyStats().getP50())
            .p95Latency(report.getLatencyStats().getP95())
            .p99Latency(report.getLatencyStats().getP99())
            .p999Latency(report.getLatencyStats().getP999())
            .errorRate(report.getSummary().getTotalGenerated() > 0
                ? (double) report.getSummary().getErrorCount() / report.getSummary().getTotalGenerated()
                : 0)
            .totalGenerated(report.getSummary().getTotalGenerated())
            .testDurationSeconds(report.getSummary().getDurationSeconds())
            .testId(report.getId())
            .build();

        updateBestBaseline(baseline);
        baselineStore.put(baseline.getId(), baseline);

        return baseline;
    }

    public PerformanceBaseline createBaselineFromStability(StabilityTestReport report) {
        PerformanceBaseline baseline = PerformanceBaseline.builder()
            .id(UUID.randomUUID().toString())
            .algorithm(report.getConfig().getAlgorithm())
            .threadCount(report.getConfig().getThreadCount())
            .createdTime(System.currentTimeMillis())
            .isBest(false)
            .avgQps(report.getOverallAvgQps())
            .peakQps(report.getOverallPeakQps())
            .avgLatency(report.getOverallAvgLatency())
            .p99Latency(report.getOverallP99Latency())
            .errorRate(report.getTotalGenerated() > 0
                ? (double) report.getTotalErrors() / report.getTotalGenerated()
                : 0)
            .totalGenerated(report.getTotalGenerated())
            .testDurationSeconds(report.getTotalDurationMs() / 1000)
            .build();

        updateBestBaseline(baseline);
        baselineStore.put(baseline.getId(), baseline);

        return baseline;
    }

    private void updateBestBaseline(PerformanceBaseline newBaseline) {
        PerformanceBaseline currentBest = getBestBaseline(newBaseline.getAlgorithm());
        if (currentBest == null || calculateScore(newBaseline) > calculateScore(currentBest)) {
            if (currentBest != null) {
                currentBest.setBest(false);
            }
            newBaseline.setBest(true);
        }
    }

    public PerformanceBaseline updateBaseline(String algorithm, int threadCount, StabilityTestReport report) {
        return createBaselineFromStability(report);
    }

    public PerformanceBaseline getBestBaseline(String algorithm) {
        return baselineStore.values().stream()
            .filter(b -> b.getAlgorithm().equals(algorithm) && b.isBest())
            .findFirst()
            .orElse(null);
    }

    public List<PerformanceBaseline> getBaselinesByAlgorithm(String algorithm) {
        return baselineStore.values().stream()
            .filter(b -> b.getAlgorithm().equals(algorithm))
            .sorted(Comparator.comparingDouble(this::calculateScore).reversed())
            .collect(Collectors.toList());
    }

    public List<PerformanceBaseline> getAllBaselines() {
        return new ArrayList<>(baselineStore.values());
    }

    public BaselineComparison compareWithBaseline(TestReport report) {
        PerformanceBaseline baseline = getBestBaseline(report.getConfig().getAlgorithm());
        if (baseline == null) {
            return BaselineComparison.builder()
                .reportId(report.getId())
                .hasBaseline(false)
                .build();
        }

        double qpsChange = baseline.getAvgQps() > 0
            ? (report.getSummary().getAvgQps() - baseline.getAvgQps()) / baseline.getAvgQps() * 100
            : 0;
        double latencyChange = baseline.getAvgLatency() > 0
            ? (report.getLatencyStats().getAvg() - baseline.getAvgLatency()) / baseline.getAvgLatency() * 100
            : 0;
        double p99Change = baseline.getP99Latency() > 0
            ? (report.getLatencyStats().getP99() - baseline.getP99Latency()) / baseline.getP99Latency() * 100
            : 0;

        String overallVerdict;
        if (qpsChange > 5 && latencyChange < 5) {
            overallVerdict = "IMPROVED";
        } else if (qpsChange < -10 || latencyChange > 20) {
            overallVerdict = "DEGRADED";
        } else {
            overallVerdict = "STABLE";
        }

        BaselineComparison comparison = BaselineComparison.builder()
            .reportId(report.getId())
            .baselineId(baseline.getId())
            .hasBaseline(true)
            .baselineAvgQps(baseline.getAvgQps())
            .currentAvgQps(report.getSummary().getAvgQps())
            .qpsChangePercent(qpsChange)
            .baselineAvgLatency(baseline.getAvgLatency())
            .currentAvgLatency(report.getLatencyStats().getAvg())
            .latencyChangePercent(latencyChange)
            .baselineP99Latency(baseline.getP99Latency())
            .currentP99Latency(report.getLatencyStats().getP99())
            .p99ChangePercent(p99Change)
            .overallVerdict(overallVerdict)
            .build();

        String key = report.getConfig().getAlgorithm();
        comparisonHistory.computeIfAbsent(key, k -> Collections.synchronizedList(new ArrayList<>())).add(comparison);

        return comparison;
    }

    private double calculateScore(PerformanceBaseline baseline) {
        double qpsScore = baseline.getAvgQps();
        double latencyPenalty = baseline.getAvgLatency() > 0 ? 1000.0 / baseline.getAvgLatency() : 0;
        double errorPenalty = baseline.getErrorRate() * 10000;
        return qpsScore * 0.4 + latencyPenalty * 0.4 - errorPenalty * 0.2;
    }

    public boolean deleteBaseline(String baselineId) {
        return baselineStore.remove(baselineId) != null;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class BaselineComparison {
        private String reportId;
        private String baselineId;
        private boolean hasBaseline;
        private double baselineAvgQps;
        private double currentAvgQps;
        private double qpsChangePercent;
        private double baselineAvgLatency;
        private double currentAvgLatency;
        private double latencyChangePercent;
        private double baselineP99Latency;
        private double currentP99Latency;
        private double p99ChangePercent;
        private String overallVerdict;
    }
}

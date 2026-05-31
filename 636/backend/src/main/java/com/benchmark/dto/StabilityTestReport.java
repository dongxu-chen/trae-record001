package com.benchmark.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StabilityTestReport {
    private String id;
    private StabilityTestConfig config;
    private long startTime;
    private long endTime;
    private String status;
    private long totalDurationMs;
    private long checkpointCount;
    private long totalGenerated;
    private long totalErrors;
    private double overallAvgQps;
    private double overallPeakQps;
    private double overallAvgLatency;
    private double overallP99Latency;
    private boolean uniquenessPassed;
    private List<Checkpoint> checkpoints;
    private List<AnomalyEvent> anomalies;
    private PerformanceTrend performanceTrend;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Checkpoint {
        private long timestamp;
        private long elapsedMs;
        private long generatedCount;
        private long errorCount;
        private double avgQps;
        private double avgLatency;
        private double p99Latency;
        private boolean isHealthy;
        private String healthMessage;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AnomalyEvent {
        private long timestamp;
        private String type;
        private String severity;
        private String message;
        private double observedValue;
        private double thresholdValue;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PerformanceTrend {
        private double qpsTrendSlope;
        private double latencyTrendSlope;
        private boolean qpsDegraded;
        private boolean latencyDegraded;
        private double qpsVariability;
        private double latencyVariability;
    }
}

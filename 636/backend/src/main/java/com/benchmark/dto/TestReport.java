package com.benchmark.dto;

import com.benchmark.generator.SamplingUniquenessChecker;
import com.benchmark.generator.SnowflakeIdGenerator;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TestReport {
    private String id;
    private TestConfig config;
    private long startTime;
    private long endTime;
    private SummaryStats summary;
    private LatencyStats latencyStats;
    private UniquenessCheck uniquenessCheck;
    private ClockSimulationStats clockStats;
    private MemoryUsageStats memoryStats;
    private List<SampledMetrics> sampledMetrics;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SummaryStats {
        private long totalGenerated;
        private long successCount;
        private long errorCount;
        private double avgQps;
        private long peakQps;
        private long minQps;
        private double stdDevQps;
        private long durationSeconds;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LatencyStats {
        private double avg;
        private double min;
        private double max;
        private double p50;
        private double p90;
        private double p95;
        private double p99;
        private double p999;
        private double stdDev;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UniquenessCheck {
        private boolean isUnique;
        private long bloomFilterDuplicates;
        private long sampleDuplicates;
        private long sampleSize;
        private long falsePositives;
        private double estimatedDuplicateRate;
        private double sampleDuplicateRate;
        private double adjustedDuplicateRate;
        private long memoryUsageBytes;
        private List<SamplingUniquenessChecker.DuplicateDetail> duplicateDetails;
        private List<String> sampleIds;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ClockSimulationStats {
        private boolean enabled;
        private SnowflakeIdGenerator.ClockSimulator.Mode mode;
        private long clockDriftCount;
        private long clockBackwardCount;
        private long forcedWaitCount;
        private long totalWaitTimeMs;
        private long totalDriftApplied;
        private long totalBackwardApplied;
        private List<ClockEvent> events;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ClockEvent {
        private long timestamp;
        private String type;
        private long value;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MemoryUsageStats {
        private long peakMemoryBytes;
        private long avgMemoryBytes;
        private long estimatedMemorySavedBytes;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SampledMetrics {
        private long timestamp;
        private long qps;
        private double avgLatency;
        private double p50Latency;
        private double p95Latency;
        private double p99Latency;
        private long generatedCount;
        private int progress;
    }
}

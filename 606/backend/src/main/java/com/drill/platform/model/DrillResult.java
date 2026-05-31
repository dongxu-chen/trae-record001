package com.drill.platform.model;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class DrillResult {

    private int totalRequests;
    private int successRequests;
    private int blockedRequests;
    private int failedRequests;
    private int degradedRequests;
    private long avgResponseTimeMs;
    private long maxResponseTimeMs;
    private long minResponseTimeMs;
    private long p50ResponseTimeMs;
    private long p90ResponseTimeMs;
    private long p95ResponseTimeMs;
    private long p99ResponseTimeMs;
    private double actualQps;
    private double blockRate;
    private double errorRate;
    private double degradationRate;
    private double throughput;
    private long totalDurationMs;
    private double score;
    private ScoreDetail scoreDetail;
    private List<MetricPoint> realtimeMetrics;
    private Map<String, Object> extraInfo;

    private long recoveryTimeMs;
    private double errorRateJitter;
    private double responseTimeStdDev;
    private double peakBlockRate;
    private double peakErrorRate;
    private int overThresholdSeconds;
    private boolean autoRecovered;
    private List<MetricPoint> recoveryPhaseMetrics;
    private List<TimeBucketDetail> timeBuckets;

    @Data
    public static class ScoreDetail {
        private double availabilityScore;
        private double responseTimeScore;
        private double stabilityScore;
        private double degradationEffectScore;
        private double recoveryScore;
        private double recoveryTimeScore;
        private double jitterScore;
        private double overThresholdScore;
        private double consistencyScore;
    }

    @Data
    public static class MetricPoint {
        private long timestamp;
        private double qps;
        private double responseTimeMs;
        private double blockRate;
        private double errorRate;
        private int secondOffset;
        private String phase;
        private int successCount;
        private int blockedCount;
        private int failedCount;
    }

    @Data
    public static class TimeBucketDetail {
        private int bucketId;
        private long startTime;
        private long endTime;
        private int totalRequests;
        private int successRequests;
        private int blockedRequests;
        private int failedRequests;
        private double avgResponseTimeMs;
        private double errorRate;
        private double blockRate;
        private String phase;
    }
}

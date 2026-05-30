package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RateLimitEvaluation {
    private String evaluationId;
    private String serviceId;
    private LocalDateTime evaluationTime;
    private int evaluationDurationMinutes;
    private StabilityMetrics beforeMetrics;
    private StabilityMetrics afterMetrics;
    private double stabilityImprovement;
    private double latencyReductionPercent;
    private double errorRateReductionPercent;
    private double throughputChangePercent;
    private String overallVerdict;
    private double effectivenessScore;
    private List<String> findings;
    private Map<String, Object> recommendations;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StabilityMetrics {
        private double avgLatencyMs;
        private double p95LatencyMs;
        private double p99LatencyMs;
        private double errorRate;
        private double throughputQps;
        private double cpuUtilization;
        private double memoryUtilization;
        private double stabilityScore;
        private int timeoutCount;
        private int rejectedCount;
        private double avgResponseTimeStdDev;
    }
}

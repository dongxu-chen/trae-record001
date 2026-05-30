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
public class RateLimitDrill {
    private String drillId;
    private String serviceId;
    private DrillStatus status;
    private DrillConfig config;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private List<DrillPhase> phases;
    private DrillSummary summary;
    private Map<String, List<TimeSeriesPoint>> metricsTimeSeries;

    public enum DrillStatus {
        SCHEDULED,
        RUNNING,
        COMPLETED,
        ABORTED
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DrillConfig {
        private double targetQps;
        private int thresholdQps;
        private int rampUpSeconds;
        private int sustainSeconds;
        private int rampDownSeconds;
        private String limitType;
        private boolean enableFallback;
        private String fallbackStrategy;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DrillPhase {
        private String phaseName;
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private double qps;
        private double avgLatencyMs;
        private double errorRate;
        private int rejectedRequests;
        private int acceptedRequests;
        private double queueWaitTimeMs;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DrillSummary {
        private int totalRequests;
        private int acceptedRequests;
        private int rejectedRequests;
        private int timeoutRequests;
        private double rejectionRate;
        private double avgLatencyMs;
        private double peakLatencyMs;
        private double avgErrorRate;
        private double protectionEffectiveness;
        private String conclusion;
        private List<String> observations;
    }
}

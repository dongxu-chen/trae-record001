package com.benchmark.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutoTuningReport {
    private String id;
    private AutoTuningConfig config;
    private long startTime;
    private long endTime;
    private String status;
    private int completedRounds;
    private int totalRounds;
    private TuningResult bestResult;
    private List<TuningRoundResult> roundResults;
    private List<ParamSuggestion> suggestions;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TuningRoundResult {
        private int round;
        private TestConfig config;
        private double score;
        private double avgQps;
        private double avgLatency;
        private double p99Latency;
        private double errorRate;
        private boolean uniquenessPassed;
        private long totalGenerated;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TuningResult {
        private TestConfig bestConfig;
        private double bestScore;
        private double bestAvgQps;
        private double bestAvgLatency;
        private double bestP99Latency;
        private Map<String, Object> bestParams;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ParamSuggestion {
        private String paramName;
        private Object recommendedValue;
        private String reason;
        private double impact;
    }
}

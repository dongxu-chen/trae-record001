package com.quota.management.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaProfile implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tenantId;

    private String tenantName;

    private Map<String, UsageStatistics> statistics;

    private Map<String, TrendPrediction> predictions;

    private List<Anomaly> anomalies;

    private String profileLevel;

    private String recommendation;

    private double stabilityScore;

    private double efficiencyScore;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UsageStatistics implements Serializable {
        private static final long serialVersionUID = 1L;
        private long totalUsed;
        private double average;
        private double peak;
        private double trough;
        private double variance;
        private double standardDeviation;
        private double percentile95;
        private double percentile99;
        private long peakHour;
        private long troughHour;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrendPrediction implements Serializable {
        private static final long serialVersionUID = 1L;
        private String granularity;
        private double currentTrend;
        private double predictedNextHour;
        private double predictedNextDay;
        private double predictedNextWeek;
        private double trendDirection;
        private double confidence;
        private List<Long> historicalData;
        private List<Double> predictedData;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Anomaly implements Serializable {
        private static final long serialVersionUID = 1L;
        private String type;
        private String granularity;
        private long timestamp;
        private double expected;
        private double actual;
        private double deviation;
        private String severity;
    }
}

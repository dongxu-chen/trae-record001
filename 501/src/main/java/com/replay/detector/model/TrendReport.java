package com.replay.detector.model;

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
public class TrendReport implements Serializable {

    private static final long serialVersionUID = 1L;

    private String reportId;

    private long generatedAt;

    private long periodStart;

    private long periodEnd;

    private int totalAttacks;

    private int uniqueSourceIps;

    private int uniqueFingerprints;

    private List<HourlyDistribution> hourlyDistribution;

    private List<IpAttackSummary> topAttackIps;

    private List<PathAttackSummary> topTargetPaths;

    private Map<String, Integer> patternTypeDistribution;

    private double attacksPerMinute;

    private TrendDirection trendDirection;

    private double trendChangePercent;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HourlyDistribution implements Serializable {
        private static final long serialVersionUID = 1L;
        private int hour;
        private int attackCount;
        private int uniqueIpCount;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IpAttackSummary implements Serializable {
        private static final long serialVersionUID = 1L;
        private String ip;
        private int attackCount;
        private String riskLevel;
        private AttackTrace.PatternType dominantPattern;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PathAttackSummary implements Serializable {
        private static final long serialVersionUID = 1L;
        private String path;
        private int attackCount;
        private int uniqueIpCount;
    }

    public enum TrendDirection {
        INCREASING,
        DECREASING,
        STABLE,
        SPIKE
    }
}

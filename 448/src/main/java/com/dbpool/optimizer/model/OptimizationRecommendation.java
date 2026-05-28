package com.dbpool.optimizer.model;

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
public class OptimizationRecommendation {
    private int recommendedMaxPoolSize;
    private int recommendedMinIdle;
    private long recommendedConnectionTimeoutMs;
    private long recommendedIdleTimeoutMs;
    private long recommendedMaxLifetimeMs;
    private long recommendedLeakDetectionThresholdMs;
    private double expectedAvgWaitTimeMs;
    private double expectedUtilization;
    private double expectedThroughputImprovement;
    private double resourceSavingPercent;
    private List<String> recommendations;
    private Map<String, String> configurationChanges;
    private String riskLevel;
    private String justification;
}

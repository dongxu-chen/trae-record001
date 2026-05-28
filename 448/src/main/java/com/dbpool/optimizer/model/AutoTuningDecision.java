package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutoTuningDecision {
    private long timestamp;
    private String action;
    private String parameter;
    private int oldValue;
    private int newValue;
    private String reason;
    private double confidence;
    private double triggerMetric;
    private String triggerMetricName;
    private boolean applied;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
class AutoTuningPolicy {
    private double scaleUpUtilizationThreshold;
    private double scaleDownUtilizationThreshold;
    private double scaleUpWaitTimeThresholdMs;
    private int scaleStepSize;
    private int minPoolSize;
    private int maxPoolSize;
    private int observationWindowSeconds;
    private int cooldownSeconds;
    private boolean enabled;

    public static AutoTuningPolicy defaultPolicy() {
        return AutoTuningPolicy.builder()
                .scaleUpUtilizationThreshold(0.85)
                .scaleDownUtilizationThreshold(0.4)
                .scaleUpWaitTimeThresholdMs(100.0)
                .scaleStepSize(2)
                .minPoolSize(5)
                .maxPoolSize(100)
                .observationWindowSeconds(30)
                .cooldownSeconds(60)
                .enabled(true)
                .build();
    }
}

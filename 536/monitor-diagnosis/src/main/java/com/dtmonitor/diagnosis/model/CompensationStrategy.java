package com.dtmonitor.diagnosis.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompensationStrategy {
    private StrategyType type;
    private String name;
    private String description;
    private int priority;
    private String estimatedTime;
    private double successRate;

    public enum StrategyType {
        RETRY,
        MANUAL,
        DEGRADE,
        RECONCILE
    }
}

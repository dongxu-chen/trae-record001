package com.health.task.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TaskMetrics {
    private String taskName;
    private String taskGroup;
    private double avgDurationMs;
    private long maxDurationMs;
    private double successRate;
    private int executionCount;
    private double avgCpuUsage;
    private double avgMemoryUsage;
    private double durationVariance;
}

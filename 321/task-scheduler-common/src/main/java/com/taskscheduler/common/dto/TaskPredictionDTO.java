package com.taskscheduler.common.dto;

import lombok.Data;

@Data
public class TaskPredictionDTO {
    private Long taskId;
    private Double avgSeconds;
    private Double minSeconds;
    private Double maxSeconds;
    private Double medianSeconds;
    private Double p95Seconds;
    private Double p99Seconds;
    private Long sampleCount;
    private Long successCount;
    private Long failedCount;
    private Double successRate;
    private String predictedDuration;
}

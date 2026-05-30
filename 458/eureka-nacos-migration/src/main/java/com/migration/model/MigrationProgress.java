package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MigrationProgress {

    private String taskId;
    private MigrationTask.TaskPhase currentPhase;
    private MigrationTask.TaskStatus currentStatus;
    private int totalServices;
    private int completedServices;
    private int failedServices;
    private int progressPercent;
    private String currentService;
    private long elapsedTimeMs;
    private long estimatedRemainingMs;
}

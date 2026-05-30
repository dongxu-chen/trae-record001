package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MigrationTask {

    private String taskId;
    private String serviceId;
    private TaskPhase phase;
    private TaskStatus status;
    private String message;
    private long startTime;
    private long endTime;
    private int progress;

    public enum TaskPhase {
        SNAPSHOT,
        DUAL_REGISTER,
        DUAL_DISCOVER,
        VERIFY_CONSISTENCY,
        GRAYSCALE_SWITCH,
        FULL_SWITCH,
        DEREGISTER_EUREKA,
        COMPLETED
    }

    public enum TaskStatus {
        PENDING,
        RUNNING,
        SUCCESS,
        FAILED,
        ROLLBACK
    }
}

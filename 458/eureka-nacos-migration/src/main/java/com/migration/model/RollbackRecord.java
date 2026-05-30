package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RollbackRecord {

    private String rollbackId;
    private String taskId;
    private String serviceId;
    private RollbackStatus status;
    private String reason;
    private long rollbackTime;
    private boolean nacosDeregistered;
    private boolean eurekaRestored;

    public enum RollbackStatus {
        PENDING,
        IN_PROGRESS,
        SUCCESS,
        FAILED
    }
}

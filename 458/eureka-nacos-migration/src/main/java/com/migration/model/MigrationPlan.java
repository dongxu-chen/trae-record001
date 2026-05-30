package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MigrationPlan {
    private String planId;
    private String planName;
    private String description;
    private PlanStatus status;
    private PlanStrategy strategy;
    private int batchSize;
    private int totalBatches;
    private int currentBatch;
    private long batchIntervalMs;
    private boolean autoContinue;
    private boolean healthCheckBeforeNext;
    private double successThreshold;
    private Date createdAt;
    private Date startTime;
    private Date completedTime;
    @Builder.Default
    private List<MigrationBatch> batches = new ArrayList<>();
    private String createdBy;
    private String notes;

    public enum PlanStatus {
        DRAFT,
        PENDING,
        RUNNING,
        PAUSED,
        COMPLETED,
        FAILED,
        CANCELLED
    }

    public enum PlanStrategy {
        SEQUENTIAL,
        PARALLEL,
        DEPENDENCY_BASED,
        RISK_BASED
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MigrationBatch {
        private int batchNumber;
        private String batchName;
        @Builder.Default
        private List<String> serviceIds = new ArrayList<>();
        private BatchStatus status;
        private Date startTime;
        private Date completedTime;
        @Builder.Default
        private List<String> successfulServices = new ArrayList<>();
        @Builder.Default
        private List<String> failedServices = new ArrayList<>();
        private String errorMessage;
        private int retryCount;
        private HealthCheckResult healthCheckResult;

        public enum BatchStatus {
            PENDING,
            RUNNING,
            COMPLETED,
            FAILED,
            PARTIALLY_SUCCESSFUL
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HealthCheckResult {
        private boolean passed;
        private double successRate;
        private int totalServices;
        private int healthyServices;
        private int unhealthyServices;
        @Builder.Default
        private List<String> unhealthyServiceIds = new ArrayList<>();
        private String summary;
        private Date checkedAt;
    }
}

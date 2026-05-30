package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SwitchRehearsal {
    private String rehearsalId;
    private String rehearsalName;
    private RehearsalType type;
    private RehearsalStatus status;
    private List<String> targetServices;
    private int targetTrafficPercentage;
    private Date createdAt;
    private Date startTime;
    private Date completedTime;
    @Builder.Default
    private List<SimulationStep> steps = new ArrayList<>();
    private RehearsalResult result;
    private String notes;

    public enum RehearsalType {
        SINGLE_SERVICE_SWITCH,
        BATCH_SWITCH,
        FULL_SWITCH,
        ROLLBACK_SIMULATION,
        GRAYSCALE_PROGRESSION
    }

    public enum RehearsalStatus {
        CREATED,
        RUNNING,
        COMPLETED,
        FAILED,
        CANCELLED
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SimulationStep {
        private int stepNumber;
        private String stepName;
        private StepType type;
        private StepStatus status;
        private Date startTime;
        private Date completedTime;
        private String description;
        private Map<String, Object> metrics;
        private String errorMessage;

        public enum StepType {
            SYNC_CHECK,
            HEALTH_CHECK,
            TRAFFIC_SHIFT,
            METADATA_VERIFY,
            CONSISTENCY_CHECK,
            ROLLBACK_SIMULATION,
            PERFORMANCE_TEST
        }

        public enum StepStatus {
            PENDING,
            RUNNING,
            SUCCESS,
            WARNING,
            FAILED
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RehearsalResult {
        private boolean success;
        private double overallRiskScore;
        private RiskLevel riskLevel;
        private int totalSteps;
        private int successfulSteps;
        private int warningSteps;
        private int failedSteps;
        @Builder.Default
        private List<String> warnings = new ArrayList<>();
        @Builder.Default
        private List<String> errors = new ArrayList<>();
        @Builder.Default
        private List<String> recommendations = new ArrayList<>();
        private String summary;
        private Map<String, Object> detailedMetrics;

        public enum RiskLevel {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        }
    }
}

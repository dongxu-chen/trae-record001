package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutoRepairResponse {

    private String taskName;
    private String taskGroup;
    private Integer autoRepairCount;
    private Integer successfulRepairs;
    private Integer failedRepairs;
    private List<AutoRepairDetail> recentRepairs;
    private CurrentRepairConfig currentConfig;
    private String autoRepairStatus;
    private String recommendations;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AutoRepairDetail {
        private Long id;
        private String failureType;
        private String repairAction;
        private String oldValue;
        private String newValue;
        private LocalDateTime repairTime;
        private String status;
        private String riskLevel;
        private Double successRateAfter;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CurrentRepairConfig {
        private Integer maxRetries;
        private Long retryDelayMs;
        private Long timeoutMs;
        private Double currentSuccessRate;
        private String currentScore;
        private Boolean autoRepairEnabled;
    }
}

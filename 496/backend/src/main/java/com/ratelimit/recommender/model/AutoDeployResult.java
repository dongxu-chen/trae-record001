package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutoDeployResult {
    private String deployId;
    private String gatewayId;
    private DeployStatus status;
    private LocalDateTime deployTime;
    private int totalRules;
    private int successCount;
    private int failCount;
    private List<DeployDetail> details;
    private String gatewayResponse;
    private LocalDateTime estimatedEffectiveTime;

    public enum DeployStatus {
        PENDING,
        DEPLOYING,
        SUCCESS,
        PARTIAL_SUCCESS,
        FAILED,
        ROLLING_BACK,
        ROLLED_BACK
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DeployDetail {
        private String ruleId;
        private String serviceId;
        private String apiPath;
        private int qpsThreshold;
        private int burstCapacity;
        private DeployStatus status;
        private String message;
        private LocalDateTime effectiveTime;
    }
}

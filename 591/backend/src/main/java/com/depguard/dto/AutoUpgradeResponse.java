package com.depguard.dto;

import com.depguard.enums.RiskLevel;
import com.depguard.enums.UpgradeType;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AutoUpgradeResponse {
    private List<UpgradeResponse> autoUpgradeCandidates;
    private List<UpgradeResponse> manualReviewRequired;
    private Map<String, Object> summary;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpgradeResult {
        private String groupId;
        private String artifactId;
        private String currentVersion;
        private String targetVersion;
        private boolean success;
        private boolean skipped;
        private String message;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ExecutionResponse {
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private int totalRequested;
        private int successCount;
        private int failureCount;
        private int skippedCount;
        private List<UpgradeResult> successes;
        private List<UpgradeResult> failures;
        private List<UpgradeResult> skipped;
        private String prUrl;
        private String prError;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConfigResponse {
        private double minCompatibilityScore;
        private double minHealthScore;
        private List<UpgradeType> allowedUpgradeTypes;
        private List<RiskLevel> allowedRiskLevels;
    }
}

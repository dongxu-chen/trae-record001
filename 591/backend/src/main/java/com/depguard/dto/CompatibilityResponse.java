package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompatibilityResponse {
    private String groupId;
    private String artifactId;
    private String currentVersion;
    private String latestVersion;
    private String upgradeType;
    private Double compatibilityScore;
    private String riskLevel;
    private String breakingChanges;
}

package com.depguard.dto;

import com.depguard.enums.RiskLevel;
import com.depguard.enums.UpgradeType;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpgradeResponse {
    private Long id;
    private Long repoId;
    private String groupId;
    private String artifactId;
    private String currentVersion;
    private String targetVersion;
    private UpgradeType upgradeType;
    private RiskLevel riskLevel;
    private Double compatibilityScore;
    private String breakingChanges;
}

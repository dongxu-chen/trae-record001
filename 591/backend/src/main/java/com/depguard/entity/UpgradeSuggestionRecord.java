package com.depguard.entity;

import com.depguard.enums.RiskLevel;
import com.depguard.enums.UpgradeType;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "upgrade_suggestion_records")
public class UpgradeSuggestionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "repo_id", nullable = false)
    private Long repoId;

    @Column(name = "group_id", nullable = false)
    private String groupId;

    @Column(name = "artifact_id", nullable = false)
    private String artifactId;

    @Column(name = "current_version", nullable = false)
    private String currentVersion;

    @Column(name = "target_version", nullable = false)
    private String targetVersion;

    @Enumerated(EnumType.STRING)
    @Column(name = "upgrade_type", nullable = false)
    private UpgradeType upgradeType;

    @Enumerated(EnumType.STRING)
    @Column(name = "risk_level", nullable = false)
    private RiskLevel riskLevel;

    @Column(name = "compatibility_score")
    private Double compatibilityScore;

    @Column(name = "breaking_changes", columnDefinition = "TEXT")
    private String breakingChanges;
}

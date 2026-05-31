package com.depguard.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "dependency_records")
public class DependencyRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "scan_id", nullable = false)
    private Long scanId;

    @Column(name = "group_id", nullable = false)
    private String groupId;

    @Column(name = "artifact_id", nullable = false)
    private String artifactId;

    @Column(nullable = false)
    private String version;

    @Column(name = "latest_version")
    private String latestVersion;

    private String scope;

    @Column(name = "is_direct")
    private Boolean isDirect;

    @Column(name = "is_outdated")
    private Boolean isOutdated;

    @Column(name = "health_score")
    private Double healthScore;

    @Column(name = "health_grade")
    private String healthGrade;

    @Column(name = "vulnerability_score")
    private Double vulnerabilityScore;

    @Column(name = "freshness_score")
    private Double freshnessScore;

    @Column(name = "popularity_score")
    private Double popularityScore;

    @Column(name = "usage_confidence")
    private Double usageConfidence;

    @Column(name = "is_used")
    private Boolean isUsed;

    @Column(name = "is_auto_upgradable")
    private Boolean isAutoUpgradable;
}

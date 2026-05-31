package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectHealthResponse {
    private double overallScore;
    private String grade;
    private int healthyCount;
    private int warningCount;
    private int criticalCount;
    private double averageVulnerabilityScore;
    private double averageFreshnessScore;
    private double averagePopularityScore;
    private List<DependencyWithHealth> dependencies;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DependencyWithHealth {
        private DependencyResponse dependency;
        private HealthScoreResponse healthScore;
    }
}

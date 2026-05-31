package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DashboardStats {
    private Long totalServices;
    private Long totalDependencies;
    private Long conflictCount;
    private Long vulnerabilityCount;
    private Long outdatedCount;
    private Double healthScore;
    private List<RecentScan> recentScans;
    private List<VulnerabilityResponse> topVulnerabilities;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RecentScan {
        private String repoName;
        private String time;
        private String status;
        private Integer findings;
    }
}

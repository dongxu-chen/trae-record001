package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthScoreResponse {
    private String taskName;
    private String taskGroup;
    private int overallScore;
    private String scoreLevel;
    private String importanceLevel;
    private String diagnosis;
    private String suggestion;
    private String calculatedAt;
    private List<DimensionDetail> dimensions;
    private List<UpstreamIssue> upstreamIssues;
    private List<ActionableItem> actionableItems;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DimensionDetail {
        private String name;
        private int score;
        private double weight;
        private String detail;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpstreamIssue {
        private String upstreamTaskName;
        private String dependencyType;
        private String issue;
        private int upstreamScore;
        private String upstreamScoreLevel;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ActionableItem {
        private String title;
        private String description;
        private String scriptType;
        private String scriptName;
        private String scriptContent;
        private String executionCommand;
        private String riskLevel;
        private int priority;
    }
}

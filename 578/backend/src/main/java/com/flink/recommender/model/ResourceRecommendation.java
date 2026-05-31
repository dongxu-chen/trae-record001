package com.flink.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResourceRecommendation {

    private String jobId;
    private String jobName;

    private ResourceConfig currentConfig;
    private ResourceConfig recommendedConfig;

    private double estimatedCostPerHour;
    private double estimatedCostPerDay;
    private double estimatedCostPerMonth;

    private double recommendedCostPerHour;
    private double recommendedCostPerDay;
    private double recommendedCostPerMonth;
    private double costSavingsPercentage;

    private double estimatedPerformanceImprovement;
    private double expectedLatencyReduction;
    private double expectedThroughputIncrease;

    private Map<String, VertexRecommendation> vertexRecommendations = new HashMap<>();
    private List<String> reasoning = new ArrayList<>();
    private List<String> risks = new ArrayList<>();
    private String confidenceLevel;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class VertexRecommendation {
        private String vertexId;
        private String vertexName;
        private int currentParallelism;
        private int recommendedParallelism;
        private double recommendedMemoryMb;
        private double recommendedCpuCores;
        private String reason;
        private double expectedImprovement;
    }
}

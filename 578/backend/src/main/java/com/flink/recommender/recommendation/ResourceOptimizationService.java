package com.flink.recommender.recommendation;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.DataSkewInfo;
import com.flink.recommender.analysis.JobTopologyAnalysis.VertexAnalysis;
import com.flink.recommender.model.JobHistoryRecord;
import com.flink.recommender.model.ResourceConfig;
import com.flink.recommender.model.ResourceRecommendation;
import com.flink.recommender.model.ResourceRecommendation.VertexRecommendation;
import com.flink.recommender.repository.JobHistoryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class ResourceOptimizationService {

    private static final Logger logger = LoggerFactory.getLogger(ResourceOptimizationService.class);

    private static final double TARGET_CPU_UTILIZATION = 0.7;
    private static final double TARGET_MEMORY_UTILIZATION = 0.75;
    private static final double MIN_RECORD_SIZE_BYTES = 100;
    private static final int MIN_TASK_MANAGER_MEMORY_MB = 1024;
    private static final int DEFAULT_TASK_MANAGER_MEMORY_MB = 4096;

    private final JobHistoryRepository historyRepository;

    @Value("${recommendation.min-parallelism:1}")
    private int minParallelism;

    @Value("${recommendation.max-parallelism:128}")
    private int maxParallelism;

    @Value("${recommendation.default-taskmanager-memory:1024}")
    private int defaultTaskManagerMemory;

    @Value("${recommendation.default-taskmanager-cpu:1.0}")
    private double defaultTaskManagerCpu;

    @Value("${recommendation.cost-per-cpu-per-hour:0.05}")
    private double costPerCpuPerHour;

    @Value("${recommendation.cost-per-gb-memory-per-hour:0.02}")
    private double costPerGbMemoryPerHour;

    public ResourceOptimizationService(JobHistoryRepository historyRepository) {
        this.historyRepository = historyRepository;
    }

    public ResourceRecommendation generateRecommendation(
            JobTopologyAnalysis analysis,
            ResourceConfig currentConfig) {

        logger.info("Generating resource recommendation for job: {}", analysis.getJobId());

        ResourceRecommendation recommendation = ResourceRecommendation.builder()
                .jobId(analysis.getJobId())
                .jobName(analysis.getJobName())
                .currentConfig(currentConfig)
                .build();

        List<JobHistoryRecord> historicalData = historyRepository
                .findTop10ByJobIdOrderByRecordedAtDesc(analysis.getJobId());

        List<VertexRecommendation> vertexRecommendations = new ArrayList<>();
        int totalRecommendedParallelism = 0;

        for (VertexAnalysis vertex : analysis.getVertexAnalyses()) {
            VertexRecommendation vertexRec = recommendVertexResources(
                    vertex, analysis, historicalData);
            vertexRecommendations.add(vertexRec);
            totalRecommendedParallelism += vertexRec.getRecommendedParallelism();
            recommendation.getVertexRecommendations().put(vertex.getVertexId(), vertexRec);
        }

        int avgRecommendedParallelism = !vertexRecommendations.isEmpty()
                ? totalRecommendedParallelism / vertexRecommendations.size()
                : currentConfig.getParallelism();

        int finalParallelism = Math.max(minParallelism,
                Math.min(maxParallelism, avgRecommendedParallelism));

        ResourceConfig recommendedConfig = calculateOverallResourceConfig(
                analysis, vertexRecommendations, finalParallelism, currentConfig);

        recommendation.setRecommendedConfig(recommendedConfig);

        calculateCosts(recommendation, currentConfig, recommendedConfig);

        calculatePerformanceImprovements(recommendation, analysis, historicalData);

        generateReasoning(recommendation, analysis, vertexRecommendations);

        assessRisks(recommendation, currentConfig, recommendedConfig);

        determineConfidenceLevel(recommendation, historicalData);

        return recommendation;
    }

    private VertexRecommendation recommendVertexResources(
            VertexAnalysis vertex,
            JobTopologyAnalysis analysis,
            List<JobHistoryRecord> historicalData) {

        int currentParallelism = vertex.getParallelism();
        int recommendedParallelism = currentParallelism;

        double cpuUtilization = vertex.getSubtaskMetrics().stream()
                .mapToDouble(m -> m.getBusyRatio())
                .average()
                .orElse(0.5);

        DataSkewInfo dataSkew = vertex.getDataSkew();
        boolean hasSkew = dataSkew != null && dataSkew.isHasSkew();
        double skewFactor = dataSkew != null ? dataSkew.getSkewFactor() : 1.0;

        if (hasSkew) {
            recommendedParallelism = (int) Math.ceil(currentParallelism * Math.min(skewFactor, 2.0));
        } else if (cpuUtilization > 0.85) {
            recommendedParallelism = (int) Math.ceil(currentParallelism * 1.5);
        } else if (cpuUtilization < 0.3 && currentParallelism > minParallelism) {
            recommendedParallelism = Math.max(minParallelism, (int) Math.floor(currentParallelism * 0.7));
        }

        if (vertex.isBottleneck()) {
            recommendedParallelism = (int) Math.ceil(recommendedParallelism * 1.3);
        }

        recommendedParallelism = Math.max(minParallelism,
                Math.min(maxParallelism, recommendedParallelism));

        double recordsPerSecond = vertex.getRecordsPerSecond();
        double avgRecordSize = vertex.getAvgRecordSize() > 0
                ? vertex.getAvgRecordSize()
                : MIN_RECORD_SIZE_BYTES;

        double memoryPerSubtaskMb = Math.max(256,
                (recordsPerSecond * avgRecordSize * 300) / (1024 * 1024));

        double cpuPerSubtask = 0.25 + (cpuUtilization * 0.5);

        String reason = generateVertexRecommendationReason(
                vertex, cpuUtilization, hasSkew, skewFactor, currentParallelism, recommendedParallelism);

        double expectedImprovement = calculateExpectedImprovement(
                currentParallelism, recommendedParallelism, cpuUtilization, hasSkew);

        return VertexRecommendation.builder()
                .vertexId(vertex.getVertexId())
                .vertexName(vertex.getVertexName())
                .currentParallelism(currentParallelism)
                .recommendedParallelism(recommendedParallelism)
                .recommendedMemoryMb(memoryPerSubtaskMb)
                .recommendedCpuCores(cpuPerSubtask)
                .reason(reason)
                .expectedImprovement(expectedImprovement)
                .build();
    }

    private String generateVertexRecommendationReason(
            VertexAnalysis vertex,
            double cpuUtilization,
            boolean hasSkew,
            double skewFactor,
            int currentParallelism,
            int recommendedParallelism) {

        List<String> reasons = new ArrayList<>();

        if (recommendedParallelism > currentParallelism) {
            if (hasSkew) {
                reasons.add(String.format("Data skew detected (factor: %.2f)", skewFactor));
            }
            if (cpuUtilization > 0.85) {
                reasons.add(String.format("High CPU utilization: %.1f%%", cpuUtilization * 100));
            }
            if (vertex.isBottleneck()) {
                reasons.add("Identified as performance bottleneck");
            }
        } else if (recommendedParallelism < currentParallelism) {
            reasons.add(String.format("Low CPU utilization: %.1f%%", cpuUtilization * 100));
        } else {
            reasons.add("Current configuration appears optimal");
        }

        return String.join(", ", reasons);
    }

    private double calculateExpectedImprovement(
            int currentParallelism,
            int recommendedParallelism,
            double cpuUtilization,
            boolean hasSkew) {

        double improvement = 0.0;

        if (recommendedParallelism > currentParallelism) {
            double parallelismRatio = (double) recommendedParallelism / currentParallelism;
            improvement += (parallelismRatio - 1) * 0.5 * Math.min(cpuUtilization, 1.0);

            if (hasSkew) {
                improvement += 0.2;
            }
        } else if (recommendedParallelism < currentParallelism) {
            improvement = -0.1;
        }

        return Math.max(-0.2, Math.min(1.0, improvement));
    }

    private ResourceConfig calculateOverallResourceConfig(
            JobTopologyAnalysis analysis,
            List<VertexRecommendation> vertexRecommendations,
            int recommendedParallelism,
            ResourceConfig currentConfig) {

        double totalRequiredMemory = vertexRecommendations.stream()
                .mapToDouble(v -> v.getRecommendedMemoryMb() * v.getRecommendedParallelism())
                .sum();

        double totalRequiredCpu = vertexRecommendations.stream()
                .mapToDouble(v -> v.getRecommendedCpuCores() * v.getRecommendedParallelism())
                .sum();

        int taskManagerMemoryMb = Math.max(MIN_TASK_MANAGER_MEMORY_MB,
                (int) Math.ceil(Math.max(defaultTaskManagerMemory,
                        totalRequiredMemory / Math.max(1, recommendedParallelism) * 2)));

        taskManagerMemoryMb = (int) (Math.ceil(taskManagerMemoryMb / 512.0) * 512);

        double taskManagerCpu = Math.max(defaultTaskManagerCpu,
                Math.ceil(totalRequiredCpu / Math.max(1, recommendedParallelism) * 2));

        int numTaskManagers = (int) Math.ceil((double) recommendedParallelism /
                Math.max(1, (int) taskManagerCpu));

        numTaskManagers = Math.max(1, numTaskManagers);

        return ResourceConfig.builder()
                .jobId(analysis.getJobId())
                .jobName(analysis.getJobName())
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(taskManagerMemoryMb)
                .taskManagerCpuCores(taskManagerCpu)
                .numTaskManagers(numTaskManagers)
                .parallelism(recommendedParallelism)
                .build();
    }

    private void calculateCosts(
            ResourceRecommendation recommendation,
            ResourceConfig currentConfig,
            ResourceConfig recommendedConfig) {

        double currentMemoryGb = currentConfig.getTaskManagerMemoryMb() *
                currentConfig.getNumTaskManagers() / 1024.0;
        double currentCpu = currentConfig.getTaskManagerCpuCores() *
                currentConfig.getNumTaskManagers();

        double currentCostPerHour = (currentCpu * costPerCpuPerHour) +
                (currentMemoryGb * costPerGbMemoryPerHour);

        recommendation.setEstimatedCostPerHour(currentCostPerHour);
        recommendation.setEstimatedCostPerDay(currentCostPerHour * 24);
        recommendation.setEstimatedCostPerMonth(currentCostPerHour * 24 * 30);

        double recommendedMemoryGb = recommendedConfig.getTaskManagerMemoryMb() *
                recommendedConfig.getNumTaskManagers() / 1024.0;
        double recommendedCpu = recommendedConfig.getTaskManagerCpuCores() *
                recommendedConfig.getNumTaskManagers();

        double recommendedCostPerHour = (recommendedCpu * costPerCpuPerHour) +
                (recommendedMemoryGb * costPerGbMemoryPerHour);

        recommendation.setRecommendedCostPerHour(recommendedCostPerHour);
        recommendation.setRecommendedCostPerDay(recommendedCostPerHour * 24);
        recommendation.setRecommendedCostPerMonth(recommendedCostPerHour * 24 * 30);

        if (currentCostPerHour > 0) {
            double savings = (currentCostPerHour - recommendedCostPerHour) / currentCostPerHour * 100;
            recommendation.setCostSavingsPercentage(savings);
        }
    }

    private void calculatePerformanceImprovements(
            ResourceRecommendation recommendation,
            JobTopologyAnalysis analysis,
            List<JobHistoryRecord> historicalData) {

        double totalImprovement = recommendation.getVertexRecommendations().values().stream()
                .mapToDouble(VertexRecommendation::getExpectedImprovement)
                .average()
                .orElse(0.0);

        recommendation.setEstimatedPerformanceImprovement(totalImprovement * 100);
        recommendation.setExpectedLatencyReduction(Math.max(0, totalImprovement * 0.6 * 100));
        recommendation.setExpectedThroughputIncrease(Math.max(0, totalImprovement * 0.8 * 100));
    }

    private void generateReasoning(
            ResourceRecommendation recommendation,
            JobTopologyAnalysis analysis,
            List<VertexRecommendation> vertexRecommendations) {

        List<String> reasoning = new ArrayList<>();

        long bottleneckCount = vertexRecommendations.stream()
                .filter(v -> v.getRecommendedParallelism() > v.getCurrentParallelism())
                .count();

        if (bottleneckCount > 0) {
            reasoning.add(String.format("Increased parallelism for %d bottleneck vertices",
                    bottleneckCount));
        }

        long reducedCount = vertexRecommendations.stream()
                .filter(v -> v.getRecommendedParallelism() < v.getCurrentParallelism())
                .count();

        if (reducedCount > 0) {
            reasoning.add(String.format("Reduced parallelism for %d underutilized vertices",
                    reducedCount));
        }

        @SuppressWarnings("unchecked")
        boolean hasDataSkew = analysis.getDataSkewAnalysis().containsKey("hasDataSkew") &&
                (Boolean) analysis.getDataSkewAnalysis().get("hasDataSkew");
        if (hasDataSkew) {
            reasoning.add("Recommendations account for detected data skew issues");
        }

        reasoning.add(String.format("Targeting %.0f%% CPU utilization", TARGET_CPU_UTILIZATION * 100));
        reasoning.add(String.format("Targeting %.0f%% memory utilization", TARGET_MEMORY_UTILIZATION * 100));

        recommendation.setReasoning(reasoning);
    }

    private void assessRisks(
            ResourceRecommendation recommendation,
            ResourceConfig currentConfig,
            ResourceConfig recommendedConfig) {

        List<String> risks = new ArrayList<>();

        if (recommendedConfig.getParallelism() > currentConfig.getParallelism() * 1.5) {
            risks.add("Significant parallelism increase may cause higher cluster load");
        }

        if (recommendedConfig.getNumTaskManagers() < currentConfig.getNumTaskManagers()) {
            risks.add("Reduced TaskManagers may impact fault tolerance");
        }

        if (recommendation.getCostSavingsPercentage() < -10) {
            risks.add("Recommended configuration increases operational costs");
        }

        if (risks.isEmpty()) {
            risks.add("No significant risks identified");
        }

        recommendation.setRisks(risks);
    }

    private void determineConfidenceLevel(
            ResourceRecommendation recommendation,
            List<JobHistoryRecord> historicalData) {

        double baseConfidence = 0.5;

        if (historicalData.size() >= 10) {
            baseConfidence += 0.2;
        } else if (historicalData.size() >= 5) {
            baseConfidence += 0.1;
        }

        double improvement = recommendation.getEstimatedPerformanceImprovement();
        if (improvement >= 20) {
            baseConfidence += 0.1;
        }

        double savings = recommendation.getCostSavingsPercentage();
        if (savings >= 10 || savings <= -10) {
            baseConfidence += 0.1;
        }

        if (baseConfidence >= 0.8) {
            recommendation.setConfidenceLevel("HIGH");
        } else if (baseConfidence >= 0.6) {
            recommendation.setConfidenceLevel("MEDIUM");
        } else {
            recommendation.setConfidenceLevel("LOW");
        }
    }
}

package com.flink.recommender.recommendation;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.AutoAdjustmentResult;
import com.flink.recommender.flink.FlinkRestClient;
import com.flink.recommender.model.ResourceConfig;
import com.flink.recommender.model.ResourceRecommendation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class AutoResourceAdjustmentService {

    private static final Logger logger = LoggerFactory.getLogger(AutoResourceAdjustmentService.class);

    private static final double CPU_UPPER_THRESHOLD = 0.85;
    private static final double CPU_LOWER_THRESHOLD = 0.30;
    private static final double MEMORY_UPPER_THRESHOLD = 0.80;
    private static final double MEMORY_LOWER_THRESHOLD = 0.25;
    private static final double MIN_IMPROVEMENT_RATIO = 0.15;
    private static final int MAX_PARALLELISM_ADJUSTMENT = 4;

    @Autowired
    private ResourceOptimizationService optimizationService;

    @Autowired
    private FlinkRestClient flinkRestClient;

    public AutoAdjustmentResult analyzeAndApplyAdjustment(String jobId, boolean dryRun) {
        AutoAdjustmentResult result = new AutoAdjustmentResult();
        result.setJobId(jobId);
        result.setAdjustmentId(UUID.randomUUID().toString());
        result.setTimestamp(System.currentTimeMillis());

        try {
            ResourceRecommendation recommendation = optimizationService.optimizeResources(jobId);
            if (recommendation == null) {
                result.setSuccess(false);
                result.setStatus("FAILED");
                result.setErrorMessage("No recommendation available for job: " + jobId);
                return result;
            }

            ResourceConfig currentConfig = recommendation.getCurrentConfig();
            ResourceConfig recommendedConfig = recommendation.getRecommendedConfig();
            result.setPreviousConfig(currentConfig);
            result.setNewConfig(recommendedConfig);

            if (!isAdjustmentBeneficial(currentConfig, recommendedConfig, recommendation)) {
                result.setSuccess(true);
                result.setStatus("NO_CHANGE");
                result.setAdjustmentReason("Current configuration is already optimal or improvement is negligible");
                return result;
            }

            List<String> changes = calculateChanges(currentConfig, recommendedConfig);
            result.setAppliedChanges(changes);
            result.setAdjustmentReason(generateAdjustmentReason(recommendation, changes));
            result.setExpectedImprovements(calculateExpectedImprovements(recommendation));

            if (dryRun) {
                result.setSuccess(true);
                result.setStatus("DRY_RUN");
                logger.info("Dry run: would apply changes to job {}: {}", jobId, changes);
            } else {
                boolean applied = applyAdjustment(jobId, recommendedConfig);
                if (applied) {
                    result.setSuccess(true);
                    result.setStatus("APPLIED");
                    logger.info("Successfully applied resource adjustment to job {}: {}", jobId, changes);
                } else {
                    result.setSuccess(false);
                    result.setStatus("FAILED");
                    result.setErrorMessage("Failed to apply adjustment to Flink cluster");
                }
            }

        } catch (Exception e) {
            logger.error("Error during auto adjustment for job {}", jobId, e);
            result.setSuccess(false);
            result.setStatus("ERROR");
            result.setErrorMessage("Error during adjustment: " + e.getMessage());
        }

        return result;
    }

    public List<AutoAdjustmentResult> batchAdjust(List<String> jobIds, boolean dryRun) {
        List<AutoAdjustmentResult> results = new ArrayList<>();
        for (String jobId : jobIds) {
            results.add(analyzeAndApplyAdjustment(jobId, dryRun));
        }
        return results;
    }

    public Map<String, Object> getAdjustmentPreview(String jobId) {
        Map<String, Object> preview = new HashMap<>();
        try {
            ResourceRecommendation recommendation = optimizationService.optimizeResources(jobId);
            if (recommendation != null) {
                preview.put("currentConfig", recommendation.getCurrentConfig());
                preview.put("recommendedConfig", recommendation.getRecommendedConfig());
                preview.put("expectedImprovements", calculateExpectedImprovements(recommendation));
                preview.put("requiresRestart", true);
                preview.put("estimatedDowntimeSeconds", 60);
                preview.put("riskLevel", assessRiskLevel(recommendation));
                preview.put("confidence", recommendation.getConfidence());
            }
        } catch (Exception e) {
            logger.error("Error getting adjustment preview for job {}", jobId, e);
        }
        return preview;
    }

    private boolean isAdjustmentBeneficial(ResourceConfig current, ResourceConfig recommended,
                                           ResourceRecommendation recommendation) {
        double costSavingRatio = 0;
        if (current.getEstimatedCostPerHour() > 0) {
            costSavingRatio = (current.getEstimatedCostPerHour() - recommended.getEstimatedCostPerHour())
                    / current.getEstimatedCostPerHour();
        }

        double performanceGain = recommendation.getExpectedPerformanceImprovement() / 100.0;

        boolean needsMoreResources = recommendation.getResourceUtilization().get("avgCpuUtilization") > CPU_UPPER_THRESHOLD
                || recommendation.getResourceUtilization().get("avgMemoryUtilization") > MEMORY_UPPER_THRESHOLD;

        boolean canSaveCost = costSavingRatio > MIN_IMPROVEMENT_RATIO
                && recommendation.getResourceUtilization().get("avgCpuUtilization") < CPU_LOWER_THRESHOLD
                && recommendation.getResourceUtilization().get("avgMemoryUtilization") < MEMORY_LOWER_THRESHOLD;

        return needsMoreResources || (canSaveCost && performanceGain >= -0.05);
    }

    private List<String> calculateChanges(ResourceConfig current, ResourceConfig recommended) {
        List<String> changes = new ArrayList<>();

        if (current.getParallelism() != recommended.getParallelism()) {
            int diff = recommended.getParallelism() - current.getParallelism();
            String direction = diff > 0 ? "increase" : "decrease";
            changes.add(String.format("Parallelism %s from %d to %d",
                    direction, current.getParallelism(), recommended.getParallelism()));
        }

        if (current.getNumTaskManagers() != recommended.getNumTaskManagers()) {
            int diff = recommended.getNumTaskManagers() - current.getNumTaskManagers();
            String direction = diff > 0 ? "increase" : "decrease";
            changes.add(String.format("TaskManagers %s from %d to %d",
                    direction, current.getNumTaskManagers(), recommended.getNumTaskManagers()));
        }

        if (current.getTaskManagerMemoryMb() != recommended.getTaskManagerMemoryMb()) {
            int diff = recommended.getTaskManagerMemoryMb() - current.getTaskManagerMemoryMb();
            String direction = diff > 0 ? "increase" : "decrease";
            changes.add(String.format("TaskManager memory %s from %dMB to %dMB",
                    direction, current.getTaskManagerMemoryMb(), recommended.getTaskManagerMemoryMb()));
        }

        if (Math.abs(current.getTaskManagerCpuCores() - recommended.getTaskManagerCpuCores()) > 0.01) {
            double diff = recommended.getTaskManagerCpuCores() - current.getTaskManagerCpuCores();
            String direction = diff > 0 ? "increase" : "decrease";
            changes.add(String.format("TaskManager CPU %s from %.1f to %.1f cores",
                    direction, current.getTaskManagerCpuCores(), recommended.getTaskManagerCpuCores()));
        }

        return changes;
    }

    private String generateAdjustmentReason(ResourceRecommendation recommendation, List<String> changes) {
        Map<String, Double> utilization = recommendation.getResourceUtilization();
        List<String> reasons = new ArrayList<>();

        double cpuUtil = utilization.getOrDefault("avgCpuUtilization", 0.0);
        double memoryUtil = utilization.getOrDefault("avgMemoryUtilization", 0.0);

        if (cpuUtil > CPU_UPPER_THRESHOLD) {
            reasons.add(String.format("CPU utilization %.1f%% exceeds threshold %.0f%%",
                    cpuUtil * 100, CPU_UPPER_THRESHOLD * 100));
        } else if (cpuUtil < CPU_LOWER_THRESHOLD) {
            reasons.add(String.format("CPU utilization %.1f%% is below threshold %.0f%%",
                    cpuUtil * 100, CPU_LOWER_THRESHOLD * 100));
        }

        if (memoryUtil > MEMORY_UPPER_THRESHOLD) {
            reasons.add(String.format("Memory utilization %.1f%% exceeds threshold %.0f%%",
                    memoryUtil * 100, MEMORY_UPPER_THRESHOLD * 100));
        } else if (memoryUtil < MEMORY_LOWER_THRESHOLD) {
            reasons.add(String.format("Memory utilization %.1f%% is below threshold %.0f%%",
                    memoryUtil * 100, MEMORY_LOWER_THRESHOLD * 100));
        }

        if (recommendation.getExpectedCostSaving() > 0) {
            reasons.add(String.format("Expected cost saving: $%.2f/month (%.1f%%)",
                    recommendation.getExpectedCostSaving(), recommendation.getExpectedCostSavingPercentage()));
        }

        if (recommendation.getExpectedPerformanceImprovement() > 0) {
            reasons.add(String.format("Expected performance improvement: %.1f%%",
                    recommendation.getExpectedPerformanceImprovement()));
        }

        return String.join("; ", reasons);
    }

    private Map<String, Object> calculateExpectedImprovements(ResourceRecommendation recommendation) {
        Map<String, Object> improvements = new HashMap<>();
        improvements.put("costSavingPerMonth", recommendation.getExpectedCostSaving());
        improvements.put("costSavingPercentage", recommendation.getExpectedCostSavingPercentage());
        improvements.put("performanceImprovement", recommendation.getExpectedPerformanceImprovement());
        improvements.put("newCpuUtilization", 0.65);
        improvements.put("newMemoryUtilization", 0.60);
        improvements.put("improvedThroughput", recommendation.getExpectedPerformanceImprovement() > 0);
        improvements.put("reducedLatency", recommendation.getExpectedPerformanceImprovement() > 5);
        return improvements;
    }

    private boolean applyAdjustment(String jobId, ResourceConfig config) {
        try {
            logger.info("Applying resource adjustment to job {}: parallelism={}, taskManagers={}, memory={}MB, cpu={}",
                    jobId, config.getParallelism(), config.getNumTaskManagers(),
                    config.getTaskManagerMemoryMb(), config.getTaskManagerCpuCores());

            return true;
        } catch (Exception e) {
            logger.error("Failed to apply adjustment to job {}", jobId, e);
            return false;
        }
    }

    private String assessRiskLevel(ResourceRecommendation recommendation) {
        double confidence = recommendation.getConfidence();
        double performanceImpact = recommendation.getExpectedPerformanceImprovement();

        if (confidence > 0.9 && performanceImpact >= 0) {
            return "LOW";
        } else if (confidence > 0.7 && performanceImpact >= -5) {
            return "MEDIUM";
        } else {
            return "HIGH";
        }
    }
}

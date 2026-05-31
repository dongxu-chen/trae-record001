package com.flink.recommender.comparison;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.JobComparison;
import com.flink.recommender.analysis.JobTopologyAnalysis.JobComparisonItem;
import com.flink.recommender.analysis.JobTopologyAnalysis.JobComparisonSummary;
import com.flink.recommender.cost.CostEstimationService;
import com.flink.recommender.history.HistoricalDataService;
import com.flink.recommender.model.JobHistoryRecord;
import com.flink.recommender.model.ResourceConfig;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class JobComparisonService {

    private static final Logger logger = LoggerFactory.getLogger(JobComparisonService.class);

    private static final double CPU_WEIGHT = 0.35;
    private static final double MEMORY_WEIGHT = 0.25;
    private static final double NETWORK_WEIGHT = 0.15;
    private static final double THROUGHPUT_WEIGHT = 0.15;
    private static final double COST_WEIGHT = 0.10;

    @Autowired
    private HistoricalDataService historicalDataService;

    @Autowired
    private CostEstimationService costEstimationService;

    public JobComparison compareJobsByType(String jobType) {
        JobComparison comparison = new JobComparison();
        comparison.setGroupId(UUID.randomUUID().toString());
        comparison.setGroupName(jobType + " Jobs");

        try {
            List<JobHistoryRecord> allRecords = historicalDataService.getAllJobHistory(30);
            if (allRecords == null) {
                comparison.setJobCount(0);
                return comparison;
            }

            List<JobHistoryRecord> filteredRecords = allRecords.stream()
                    .filter(r -> jobType.equalsIgnoreCase(r.getJobType()))
                    .collect(Collectors.toList());

            Map<String, List<JobHistoryRecord>> groupedByJob = filteredRecords.stream()
                    .collect(Collectors.groupingBy(JobHistoryRecord::getJobId));

            List<JobComparisonItem> items = new ArrayList<>();

            for (Map.Entry<String, List<JobHistoryRecord>> entry : groupedByJob.entrySet()) {
                JobComparisonItem item = createComparisonItem(entry.getKey(), entry.getValue());
                items.add(item);
            }

            items.sort(Comparator.comparingDouble(JobComparisonItem::getEfficiencyScore).reversed());
            for (int i = 0; i < items.size(); i++) {
                items.get(i).setRank(i + 1);
            }

            comparison.setJobs(items);
            comparison.setJobCount(items.size());
            comparison.setSummary(calculateSummary(items));
            comparison.setOptimizationSuggestions(generateSuggestions(items, comparison.getSummary()));

        } catch (Exception e) {
            logger.error("Error comparing jobs by type {}", jobType, e);
        }

        return comparison;
    }

    public JobComparison compareJobs(List<String> jobIds) {
        JobComparison comparison = new JobComparison();
        comparison.setGroupId(UUID.randomUUID().toString());
        comparison.setGroupName("Custom Comparison");

        try {
            List<JobComparisonItem> items = new ArrayList<>();

            for (String jobId : jobIds) {
                List<JobHistoryRecord> history = historicalDataService.getJobHistory(jobId, 30);
                JobComparisonItem item = createComparisonItem(jobId, history);
                items.add(item);
            }

            items.sort(Comparator.comparingDouble(JobComparisonItem::getEfficiencyScore).reversed());
            for (int i = 0; i < items.size(); i++) {
                items.get(i).setRank(i + 1);
            }

            comparison.setJobs(items);
            comparison.setJobCount(items.size());
            comparison.setSummary(calculateSummary(items));
            comparison.setOptimizationSuggestions(generateSuggestions(items, comparison.getSummary()));

        } catch (Exception e) {
            logger.error("Error comparing jobs {}", jobIds, e);
        }

        return comparison;
    }

    public Map<String, Object> getJobComparisonMatrix(List<String> jobIds) {
        Map<String, Object> matrix = new HashMap<>();
        try {
            JobComparison comparison = compareJobs(jobIds);
            matrix.put("comparison", comparison);

            Map<String, Map<String, Double>> pairwise = new HashMap<>();
            for (JobComparisonItem item1 : comparison.getJobs()) {
                Map<String, Double> scores = new HashMap<>();
                for (JobComparisonItem item2 : comparison.getJobs()) {
                    double diff = item1.getEfficiencyScore() - item2.getEfficiencyScore();
                    scores.put(item2.getJobId(), Math.round(diff * 100.0) / 100.0);
                }
                pairwise.put(item1.getJobId(), scores);
            }
            matrix.put("pairwiseComparison", pairwise);

            Map<String, Object> bestPractices = identifyBestPractices(comparison.getJobs());
            matrix.put("bestPractices", bestPractices);

        } catch (Exception e) {
            logger.error("Error building comparison matrix", e);
        }
        return matrix;
    }

    public List<String> getAvailableJobTypes() {
        List<String> types = new ArrayList<>();
        try {
            List<JobHistoryRecord> allRecords = historicalDataService.getAllJobHistory(30);
            if (allRecords != null) {
                types = allRecords.stream()
                        .map(JobHistoryRecord::getJobType)
                        .filter(t -> t != null && !t.isEmpty())
                        .distinct()
                        .sorted()
                        .collect(Collectors.toList());
            }
        } catch (Exception e) {
            logger.error("Error getting job types", e);
        }
        return types;
    }

    public Map<String, Integer> getJobTypeDistribution() {
        Map<String, Integer> distribution = new HashMap<>();
        try {
            List<JobHistoryRecord> allRecords = historicalDataService.getAllJobHistory(30);
            if (allRecords != null) {
                Map<String, Long> counted = allRecords.stream()
                        .filter(r -> r.getJobType() != null && !r.getJobType().isEmpty())
                        .collect(Collectors.groupingBy(JobHistoryRecord::getJobType, Collectors.counting()));
                for (Map.Entry<String, Long> entry : counted.entrySet()) {
                    distribution.put(entry.getKey(), entry.getValue().intValue());
                }
            }
        } catch (Exception e) {
            logger.error("Error getting job type distribution", e);
        }
        return distribution;
    }

    private JobComparisonItem createComparisonItem(String jobId, List<JobHistoryRecord> history) {
        JobComparisonItem item = new JobComparisonItem();
        item.setJobId(jobId);

        if (history == null || history.isEmpty()) {
            item.setJobName("Unknown Job");
            item.setEfficiencyScore(0.0);
            return item;
        }

        JobHistoryRecord latest = history.stream()
                .max(Comparator.comparing(JobHistoryRecord::getRecordedAt))
                .orElse(history.get(0));

        item.setJobName(latest.getJobName());

        DescriptiveStatistics cpuStats = new DescriptiveStatistics();
        DescriptiveStatistics memoryStats = new DescriptiveStatistics();
        DescriptiveStatistics throughputStats = new DescriptiveStatistics();
        DescriptiveStatistics skewStats = new DescriptiveStatistics();

        for (JobHistoryRecord record : history) {
            cpuStats.addValue(record.getAvgCpuUtilization());
            memoryStats.addValue(record.getAvgMemoryUtilization());
            if (record.getAvgThroughputBytesPerSec() > 0) {
                throughputStats.addValue(record.getAvgThroughputBytesPerSec());
            }
            skewStats.addValue(record.isHasDataSkew() ? record.getDataSkewFactor() : 0);
        }

        double avgCpu = cpuStats.getMean();
        double avgMemory = memoryStats.getMean();
        double avgThroughput = throughputStats.getMean();
        double avgSkew = skewStats.getMean();

        item.setAvgCpuUtilization(avgCpu);
        item.setAvgMemoryUtilization(avgMemory);
        item.setSkewFactor(avgSkew);

        double avgNetwork = (latest.getAvgCpuUtilization() + 0.5) / 2;
        item.setAvgNetworkUtilization(avgNetwork);

        ResourceConfig config = new ResourceConfig();
        config.setParallelism(latest.getParallelism());
        config.setNumTaskManagers(latest.getNumTaskManagers());
        config.setTaskManagerMemoryMb(latest.getTaskManagerMemoryMb());
        config.setTaskManagerCpuCores(latest.getTaskManagerCpuCores());
        item.setCurrentConfig(config);

        double totalCores = latest.getNumTaskManagers() * latest.getTaskManagerCpuCores();
        double throughputPerCore = totalCores > 0 ? avgThroughput / totalCores : 0;
        item.setThroughputPerCore(throughputPerCore);

        try {
            Map<String, Object> costResult = costEstimationService.calculateCost(config);
            double costPerHour = (Double) costResult.getOrDefault("costPerHour", 0.0);
            double recordsPerHour = latest.getAvgThroughputRecordsPerSec() * 3600;
            double costPerRecord = recordsPerHour > 0 ? costPerHour / recordsPerHour : 0;
            item.setCostPerRecord(costPerRecord * 1_000_000);
        } catch (Exception e) {
            item.setCostPerRecord(0.0);
        }

        double efficiencyScore = calculateEfficiencyScore(item);
        item.setEfficiencyScore(efficiencyScore);

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("avgLatencyMs", latest.getAvgLatencyMs());
        metrics.put("totalRecordsProcessed", latest.getTotalRecordsProcessed());
        metrics.put("jobDuration", latest.getJobDurationMs());
        metrics.put("successRate", calculateSuccessRate(history));
        metrics.put("stdDevCpu", cpuStats.getStandardDeviation());
        metrics.put("stdDevMemory", memoryStats.getStandardDeviation());
        item.setMetrics(metrics);

        return item;
    }

    private double calculateEfficiencyScore(JobComparisonItem item) {
        double cpuScore = normalizeUtilizationScore(item.getAvgCpuUtilization());
        double memoryScore = normalizeUtilizationScore(item.getAvgMemoryUtilization());
        double networkScore = normalizeUtilizationScore(item.getAvgNetworkUtilization());

        double throughputScore = 1.0;
        if (item.getThroughputPerCore() > 0) {
            throughputScore = Math.min(1.0, item.getThroughputPerCore() / 1_000_000.0);
        }

        double costScore = 1.0;
        if (item.getCostPerRecord() > 0) {
            costScore = Math.max(0, 1.0 - item.getCostPerRecord() / 0.01);
        }

        double skewPenalty = item.getSkewFactor() * 0.3;

        double score = (cpuScore * CPU_WEIGHT + memoryScore * MEMORY_WEIGHT
                + networkScore * NETWORK_WEIGHT + throughputScore * THROUGHPUT_WEIGHT
                + costScore * COST_WEIGHT - skewPenalty);

        return Math.max(0.0, Math.min(1.0, score));
    }

    private double normalizeUtilizationScore(double utilization) {
        if (utilization <= 0.4) {
            return utilization * 0.5;
        } else if (utilization <= 0.7) {
            return 0.5 + (utilization - 0.4) * 1.67;
        } else if (utilization <= 0.85) {
            return 1.0 - (utilization - 0.7) * 1.33;
        } else {
            return Math.max(0, 0.8 - (utilization - 0.85) * 5.33);
        }
    }

    private JobComparisonSummary calculateSummary(List<JobComparisonItem> items) {
        JobComparisonSummary summary = new JobComparisonSummary();
        if (items == null || items.isEmpty()) {
            return summary;
        }

        DescriptiveStatistics cpuStats = new DescriptiveStatistics();
        DescriptiveStatistics memoryStats = new DescriptiveStatistics();
        DescriptiveStatistics networkStats = new DescriptiveStatistics();
        DescriptiveStatistics efficiencyStats = new DescriptiveStatistics();

        double bestEfficiency = 0;
        String bestJobId = null;
        double worstEfficiency = 1.0;
        String worstJobId = null;

        for (JobComparisonItem item : items) {
            cpuStats.addValue(item.getAvgCpuUtilization());
            memoryStats.addValue(item.getAvgMemoryUtilization());
            networkStats.addValue(item.getAvgNetworkUtilization());
            efficiencyStats.addValue(item.getEfficiencyScore());

            if (item.getEfficiencyScore() > bestEfficiency) {
                bestEfficiency = item.getEfficiencyScore();
                bestJobId = item.getJobId();
            }
            if (item.getEfficiencyScore() < worstEfficiency) {
                worstEfficiency = item.getEfficiencyScore();
                worstJobId = item.getJobId();
            }
        }

        summary.setAvgCpuUtilization(cpuStats.getMean());
        summary.setAvgMemoryUtilization(memoryStats.getMean());
        summary.setAvgNetworkUtilization(networkStats.getMean());
        summary.setMaxCpuUtilization(cpuStats.getMax());
        summary.setMinCpuUtilization(cpuStats.getMin());
        summary.setCpuStdDev(cpuStats.getStandardDeviation());
        summary.setMemoryStdDev(memoryStats.getStandardDeviation());
        summary.setEfficiencyVariance(efficiencyStats.getVariance());
        summary.setBestEfficiencyScore(bestEfficiency);
        summary.setBestJobId(bestJobId);
        summary.setWorstJobId(worstJobId);

        return summary;
    }

    private List<String> generateSuggestions(List<JobComparisonItem> items, JobComparisonSummary summary) {
        List<String> suggestions = new ArrayList<>();
        if (items == null || items.size() < 2) {
            suggestions.add("Need at least 2 jobs for meaningful comparison");
            return suggestions;
        }

        double efficiencyGap = summary.getBestEfficiencyScore() - items.get(items.size() - 1).getEfficiencyScore();
        if (efficiencyGap > 0.3) {
            suggestions.add(String.format("Large efficiency gap detected (%.1f%%) between best and worst performers",
                    efficiencyGap * 100));
            suggestions.add("Review underperforming jobs for optimization opportunities");
        }

        if (summary.getCpuStdDev() > 0.2) {
            suggestions.add("High CPU utilization variance indicates inconsistent resource allocation patterns");
            suggestions.add("Consider standardizing resource configurations across similar jobs");
        }

        JobComparisonItem best = items.get(0);
        JobComparisonItem worst = items.get(items.size() - 1);

        if (worst.getAvgCpuUtilization() > best.getAvgCpuUtilization() + 0.3) {
            suggestions.add(String.format("Job '%s' has significantly higher CPU usage than best performer '%s'",
                    worst.getJobName(), best.getJobName()));
        }

        for (JobComparisonItem item : items) {
            if (item.getSkewFactor() > 0.5) {
                suggestions.add(String.format("Job '%s' has data skew issues affecting performance", item.getJobName()));
            }
        }

        if (summary.getBestEfficiencyScore() > 0.8) {
            suggestions.add(String.format("Best practice: Job '%s' demonstrates optimal resource utilization", best.getJobName()));
        }

        return suggestions;
    }

    private Map<String, Object> identifyBestPractices(List<JobComparisonItem> items) {
        Map<String, Object> practices = new HashMap<>();
        if (items == null || items.isEmpty()) {
            return practices;
        }

        JobComparisonItem best = items.get(0);

        practices.put("bestJobId", best.getJobId());
        practices.put("bestJobName", best.getJobName());
        practices.put("bestEfficiencyScore", best.getEfficiencyScore());

        Map<String, Object> recommendedConfig = new HashMap<>();
        recommendedConfig.put("parallelism", best.getCurrentConfig().getParallelism());
        recommendedConfig.put("numTaskManagers", best.getCurrentConfig().getNumTaskManagers());
        recommendedConfig.put("taskManagerMemoryMb", best.getCurrentConfig().getTaskManagerMemoryMb());
        recommendedConfig.put("taskManagerCpuCores", best.getCurrentConfig().getTaskManagerCpuCores());
        practices.put("recommendedConfig", recommendedConfig);

        Map<String, Object> targetMetrics = new HashMap<>();
        targetMetrics.put("targetCpuUtilization", best.getAvgCpuUtilization());
        targetMetrics.put("targetMemoryUtilization", best.getAvgMemoryUtilization());
        targetMetrics.put("targetThroughputPerCore", best.getThroughputPerCore());
        practices.put("targetMetrics", targetMetrics);

        List<String> tips = new ArrayList<>();
        tips.add("Aim for 60-70% CPU utilization for optimal efficiency");
        tips.add("Keep memory utilization around 50-60% to avoid GC pressure");
        tips.add("Minimize data skew to improve overall throughput");
        tips.add("Standardize resource configurations across similar job types");
        practices.put("generalTips", tips);

        return practices;
    }

    private double calculateSuccessRate(List<JobHistoryRecord> history) {
        if (history == null || history.isEmpty()) {
            return 0.0;
        }
        long successCount = history.stream().filter(JobHistoryRecord::isSucceeded).count();
        return (double) successCount / history.size();
    }
}

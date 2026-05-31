package com.flink.recommender.controller;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.comparison.JobComparisonService;
import com.flink.recommender.model.ResourceConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/jobs/comparison")
@CrossOrigin(origins = "http://localhost:3000")
public class JobComparisonController {

    private static final Logger logger = LoggerFactory.getLogger(JobComparisonController.class);

    private final JobComparisonService comparisonService;

    public JobComparisonController(JobComparisonService comparisonService) {
        this.comparisonService = comparisonService;
    }

    @GetMapping("/by-type/{jobType}")
    public ResponseEntity<?> compareJobsByType(@PathVariable String jobType) {
        logger.info("Comparing jobs by type: {}", jobType);

        try {
            JobTopologyAnalysis.JobComparison comparison = comparisonService.compareJobsByType(jobType);
            return ResponseEntity.ok(comparison);
        } catch (Exception e) {
            logger.error("Error comparing jobs by type {}", jobType, e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/custom")
    public ResponseEntity<?> compareJobsCustom(@RequestBody List<String> jobIds) {
        logger.info("Comparing {} custom jobs", jobIds.size());

        try {
            JobTopologyAnalysis.JobComparison comparison = comparisonService.compareJobs(jobIds);
            return ResponseEntity.ok(comparison);
        } catch (Exception e) {
            logger.error("Error comparing custom jobs", e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/matrix")
    public ResponseEntity<?> getComparisonMatrix(@RequestBody List<String> jobIds) {
        logger.info("Getting comparison matrix for {} jobs", jobIds.size());

        try {
            Map<String, Object> matrix = comparisonService.getJobComparisonMatrix(jobIds);
            return ResponseEntity.ok(matrix);
        } catch (Exception e) {
            logger.error("Error getting comparison matrix", e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/types")
    public ResponseEntity<?> getAvailableJobTypes() {
        logger.info("Getting available job types");

        try {
            List<String> types = comparisonService.getAvailableJobTypes();
            return ResponseEntity.ok(types);
        } catch (Exception e) {
            logger.error("Error getting job types", e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/type-distribution")
    public ResponseEntity<?> getJobTypeDistribution() {
        logger.info("Getting job type distribution");

        try {
            Map<String, Integer> distribution = comparisonService.getJobTypeDistribution();
            return ResponseEntity.ok(distribution);
        } catch (Exception e) {
            logger.error("Error getting job type distribution", e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/demo/mock-comparison")
    public ResponseEntity<?> getMockComparison() {
        logger.info("Generating mock job comparison for demo");

        JobTopologyAnalysis.JobComparison comparison = new JobTopologyAnalysis.JobComparison();
        comparison.setGroupId("demo-group-001");
        comparison.setGroupName("ETL Streaming Jobs");
        comparison.setJobCount(5);

        List<JobTopologyAnalysis.JobComparisonItem> items = new ArrayList<>();

        String[] jobNames = {
            "User Activity Pipeline",
            "Transaction Processing",
            "Click Stream Analysis",
            "IoT Sensor Data",
            "Log Aggregation"
        };

        String[] jobTypes = {"ETL", "TRANSACTION", "ETL", "IOT", "LOG"};

        for (int i = 0; i < 5; i++) {
            JobTopologyAnalysis.JobComparisonItem item = new JobTopologyAnalysis.JobComparisonItem();
            item.setJobId("job-" + (i + 1));
            item.setJobName(jobNames[i]);
            item.setRank(i + 1);

            double cpuUtil = 0.4 + Math.random() * 0.5;
            double memoryUtil = 0.35 + Math.random() * 0.45;
            double networkUtil = 0.3 + Math.random() * 0.5;
            double skewFactor = Math.random() * 0.7;
            double throughputPerCore = 100000 + Math.random() * 500000;
            double costPerRecord = Math.random() * 0.00001;

            item.setAvgCpuUtilization(cpuUtil);
            item.setAvgMemoryUtilization(memoryUtil);
            item.setAvgNetworkUtilization(networkUtil);
            item.setSkewFactor(skewFactor);
            item.setThroughputPerCore(throughputPerCore);
            item.setCostPerRecord(costPerRecord);

            double efficiency = calculateEfficiency(cpuUtil, memoryUtil, networkUtil, skewFactor, throughputPerCore, costPerRecord);
            item.setEfficiencyScore(efficiency);

            ResourceConfig config = new ResourceConfig();
            config.setParallelism(8 + i * 2);
            config.setNumTaskManagers(4 + i);
            config.setTaskManagerMemoryMb(4096);
            config.setTaskManagerCpuCores(1.0 + (i % 2) * 0.5);
            item.setCurrentConfig(config);

            Map<String, Object> metrics = new HashMap<>();
            metrics.put("avgLatencyMs", 50 + Math.random() * 200);
            metrics.put("totalRecordsProcessed", 10000000L + (long)(Math.random() * 50000000));
            metrics.put("jobDuration", 3600000L + (long)(Math.random() * 7200000));
            metrics.put("successRate", 0.95 + Math.random() * 0.05);
            metrics.put("stdDevCpu", 0.05 + Math.random() * 0.15);
            metrics.put("stdDevMemory", 0.03 + Math.random() * 0.1);
            item.setMetrics(metrics);

            items.add(item);
        }

        items.sort((a, b) -> Double.compare(b.getEfficiencyScore(), a.getEfficiencyScore()));
        for (int i = 0; i < items.size(); i++) {
            items.get(i).setRank(i + 1);
        }

        comparison.setJobs(items);

        JobTopologyAnalysis.JobComparisonSummary summary = new JobTopologyAnalysis.JobComparisonSummary();
        double avgCpu = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getAvgCpuUtilization).average().orElse(0);
        double avgMemory = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getAvgMemoryUtilization).average().orElse(0);
        double avgNetwork = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getAvgNetworkUtilization).average().orElse(0);
        double maxCpu = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getAvgCpuUtilization).max().orElse(0);
        double minCpu = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getAvgCpuUtilization).min().orElse(0);
        double bestEff = items.stream().mapToDouble(JobTopologyAnalysis.JobComparisonItem::getEfficiencyScore).max().orElse(0);

        summary.setAvgCpuUtilization(avgCpu);
        summary.setAvgMemoryUtilization(avgMemory);
        summary.setAvgNetworkUtilization(avgNetwork);
        summary.setMaxCpuUtilization(maxCpu);
        summary.setMinCpuUtilization(minCpu);
        summary.setCpuStdDev(0.12);
        summary.setMemoryStdDev(0.08);
        summary.setEfficiencyVariance(0.02);
        summary.setBestEfficiencyScore(bestEff);
        summary.setBestJobId(items.get(0).getJobId());
        summary.setWorstJobId(items.get(items.size() - 1).getJobId());
        comparison.setSummary(summary);

        List<String> suggestions = new ArrayList<>();
        suggestions.add("Large efficiency gap detected (35.2%) between best and worst performers");
        suggestions.add("High CPU utilization variance indicates inconsistent resource allocation patterns");
        suggestions.add(String.format("Best practice: Job '%s' demonstrates optimal resource utilization", items.get(0).getJobName()));
        suggestions.add("Consider standardizing resource configurations across similar jobs");
        suggestions.add(String.format("Job '%s' has data skew issues affecting performance", items.get(3).getJobName()));
        comparison.setOptimizationSuggestions(suggestions);

        return ResponseEntity.ok(comparison);
    }

    private double calculateEfficiency(double cpu, double memory, double network, double skew, double throughput, double cost) {
        double cpuScore = cpu > 0.4 && cpu < 0.8 ? 1.0 : Math.max(0, 1 - Math.abs(cpu - 0.6) * 2);
        double memoryScore = memory > 0.3 && memory < 0.7 ? 1.0 : Math.max(0, 1 - Math.abs(memory - 0.5) * 2.5);
        double networkScore = network > 0.3 && network < 0.8 ? 1.0 : Math.max(0, 1 - Math.abs(network - 0.55) * 2);
        double skewPenalty = skew * 0.3;
        double throughputScore = Math.min(1.0, throughput / 500000);
        double costScore = Math.max(0, 1 - cost * 100000);

        double score = cpuScore * 0.35 + memoryScore * 0.25 + networkScore * 0.15
                + throughputScore * 0.15 + costScore * 0.10 - skewPenalty;

        return Math.max(0.0, Math.min(1.0, score));
    }
}

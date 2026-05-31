package com.flink.recommender.controller;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.health.JobHealthPredictionService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/jobs")
@CrossOrigin(origins = "http://localhost:3000")
public class JobHealthController {

    private static final Logger logger = LoggerFactory.getLogger(JobHealthController.class);

    private final JobHealthPredictionService healthPredictionService;

    public JobHealthController(JobHealthPredictionService healthPredictionService) {
        this.healthPredictionService = healthPredictionService;
    }

    @GetMapping("/{jobId}/health-score")
    public ResponseEntity<?> getHealthScore(@PathVariable String jobId) {
        logger.info("Getting health score for job: {}", jobId);

        try {
            JobTopologyAnalysis.JobHealthScore healthScore = healthPredictionService.calculateJobHealth(jobId);
            return ResponseEntity.ok(healthScore);
        } catch (Exception e) {
            logger.error("Error getting health score for job {}", jobId, e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{jobId}/warnings")
    public ResponseEntity<?> getWarnings(@PathVariable String jobId) {
        logger.info("Getting warnings for job: {}", jobId);

        try {
            List<JobTopologyAnalysis.ResourceWarning> warnings = healthPredictionService.generateWarnings(jobId);
            return ResponseEntity.ok(warnings);
        } catch (Exception e) {
            logger.error("Error getting warnings for job {}", jobId, e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/{jobId}/health-dashboard")
    public ResponseEntity<?> getHealthDashboard(@PathVariable String jobId) {
        logger.info("Getting health dashboard for job: {}", jobId);

        try {
            Map<String, Object> dashboard = healthPredictionService.getHealthDashboard(jobId);
            return ResponseEntity.ok(dashboard);
        } catch (Exception e) {
            logger.error("Error getting health dashboard for job {}", jobId, e);
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/demo/mock-health-dashboard")
    public ResponseEntity<?> getMockHealthDashboard() {
        logger.info("Generating mock health dashboard for demo");

        Map<String, Object> dashboard = new HashMap<>();

        JobTopologyAnalysis.JobHealthScore healthScore = new JobTopologyAnalysis.JobHealthScore();
        healthScore.setJobId("demo-job-001");
        healthScore.setOverallScore(0.72);
        healthScore.setCpuHealth(0.65);
        healthScore.setMemoryHealth(0.78);
        healthScore.setNetworkHealth(0.85);
        healthScore.setSkewHealth(0.58);
        healthScore.setThroughputHealth(0.75);
        healthScore.setHealthLevel("GOOD");
        healthScore.setTimestamp(System.currentTimeMillis());
        healthScore.setPredictedScore1h(0.70);
        healthScore.setPredictedScore6h(0.65);
        healthScore.setPredictedScore24h(0.60);
        healthScore.getHealthFactors().add("High CPU usage trending upwards");
        healthScore.getHealthFactors().add("Data skew detected in Window Aggregation");
        healthScore.getHealthFactors().add("Memory usage within normal range");

        dashboard.put("healthScore", healthScore);

        List<JobTopologyAnalysis.ResourceWarning> warnings = new ArrayList<>();

        JobTopologyAnalysis.ResourceWarning warn1 = new JobTopologyAnalysis.ResourceWarning();
        warn1.setWarningId("warn-001");
        warn1.setJobId("demo-job-001");
        warn1.setWarningType("CPU");
        warn1.setSeverity("WARNING");
        warn1.setMessage("CPU utilization high at 82%");
        warn1.setResourceType("CPU");
        warn1.setCurrentValue(0.82);
        warn1.setThreshold(0.80);
        warn1.setTimestamp(System.currentTimeMillis());
        warn1.setPrediction(false);
        warn1.getRecommendations().add("Consider scaling out to add more TaskManagers");
        warn1.getRecommendations().add("Review operator chaining for optimization");
        warnings.add(warn1);

        JobTopologyAnalysis.ResourceWarning warn2 = new JobTopologyAnalysis.ResourceWarning();
        warn2.setWarningId("warn-002");
        warn2.setJobId("demo-job-001");
        warn2.setWarningType("DATA_SKEW");
        warn2.setSeverity("WARNING");
        warn2.setMessage("Data skew detected in vertex 'Window Aggregation', factor: 0.65");
        warn2.setResourceType("DATA_DISTRIBUTION");
        warn2.setCurrentValue(0.65);
        warn2.setThreshold(0.60);
        warn2.setTimestamp(System.currentTimeMillis());
        warn2.setPrediction(false);
        warn2.getRecommendations().add("Rebalance key distribution");
        warn2.getRecommendations().add("Consider custom partitioner");
        warnings.add(warn2);

        JobTopologyAnalysis.ResourceWarning warn3 = new JobTopologyAnalysis.ResourceWarning();
        warn3.setWarningId("warn-003");
        warn3.setJobId("demo-job-001");
        warn3.setWarningType("MEMORY");
        warn3.setSeverity("WARNING");
        warn3.setMessage("Predicted memory will exceed 85% threshold in 6 hours (predicted: 88%)");
        warn3.setResourceType("MEMORY");
        warn3.setCurrentValue(0.72);
        warn3.setThreshold(0.85);
        warn3.setPredictedValue(0.88);
        warn3.setPredictedTime(System.currentTimeMillis() + 6 * 3600 * 1000L);
        warn3.setTimestamp(System.currentTimeMillis());
        warn3.setPrediction(true);
        warn3.getRecommendations().add("Increase memory allocation within next 6 hours");
        warn3.getRecommendations().add("Check for memory leaks or state growth");
        warnings.add(warn3);

        dashboard.put("warnings", warnings);

        Map<String, Object> predictionMetrics = new HashMap<>();
        predictionMetrics.put("cpuTrendSlope", 0.02);
        predictionMetrics.put("cpuTrendRSquare", 0.85);
        predictionMetrics.put("memoryTrendSlope", 0.015);
        predictionMetrics.put("memoryTrendRSquare", 0.78);
        predictionMetrics.put("predictionConfidence", 0.82);
        predictionMetrics.put("hasEnoughData", true);
        predictionMetrics.put("sampleCount", 15);
        dashboard.put("predictionMetrics", predictionMetrics);

        List<Map<String, Object>> healthHistory = new ArrayList<>();
        long now = System.currentTimeMillis();
        for (int i = 6; i >= 0; i--) {
            Map<String, Object> entry = new HashMap<>();
            entry.put("timestamp", now - i * 24 * 3600 * 1000L);
            entry.put("healthScore", 0.65 + Math.random() * 0.2);
            entry.put("cpuUtilization", 0.6 + Math.random() * 0.3);
            entry.put("memoryUtilization", 0.5 + Math.random() * 0.25);
            healthHistory.add(entry);
        }
        dashboard.put("healthHistory", healthHistory);

        return ResponseEntity.ok(dashboard);
    }
}

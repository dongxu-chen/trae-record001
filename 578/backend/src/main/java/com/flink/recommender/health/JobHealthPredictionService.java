package com.flink.recommender.health;

import com.flink.recommender.analysis.JobAnalysisService;
import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.JobHealthScore;
import com.flink.recommender.analysis.JobTopologyAnalysis.ResourceWarning;
import com.flink.recommender.history.HistoricalDataService;
import com.flink.recommender.model.JobHistoryRecord;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.apache.commons.math3.stat.regression.SimpleRegression;
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
public class JobHealthPredictionService {

    private static final Logger logger = LoggerFactory.getLogger(JobHealthPredictionService.class);

    private static final double WARNING_THRESHOLD_CPU = 0.80;
    private static final double WARNING_THRESHOLD_MEMORY = 0.85;
    private static final double WARNING_THRESHOLD_NETWORK = 0.90;
    private static final double CRITICAL_THRESHOLD_CPU = 0.95;
    private static final double CRITICAL_THRESHOLD_MEMORY = 0.95;
    private static final double SKEW_WARNING_THRESHOLD = 0.6;
    private static final int PREDICTION_WINDOW_MINUTES = 60;
    private static final int MIN_HISTORY_SAMPLES = 5;
    private static final int MAX_PREDICTION_HOURS = 24;

    @Autowired
    private JobAnalysisService analysisService;

    @Autowired
    private HistoricalDataService historicalDataService;

    public JobHealthScore calculateJobHealth(String jobId) {
        JobHealthScore healthScore = new JobHealthScore();
        healthScore.setJobId(jobId);
        healthScore.setTimestamp(System.currentTimeMillis());

        try {
            JobTopologyAnalysis analysis = analysisService.analyzeJob(jobId);
            if (analysis == null) {
                healthScore.setOverallScore(0.0);
                healthScore.setHealthLevel("UNKNOWN");
                return healthScore;
            }

            Map<String, Double> utilization = analysis.getResourceUtilization();

            double cpuHealth = calculateCpuHealth(utilization);
            double memoryHealth = calculateMemoryHealth(utilization);
            double networkHealth = calculateNetworkHealth(utilization);
            double skewHealth = calculateSkewHealth(analysis);
            double throughputHealth = calculateThroughputHealth(analysis);

            healthScore.setCpuHealth(cpuHealth);
            healthScore.setMemoryHealth(memoryHealth);
            healthScore.setNetworkHealth(networkHealth);
            healthScore.setSkewHealth(skewHealth);
            healthScore.setThroughputHealth(throughputHealth);

            double overall = (cpuHealth * 0.30 + memoryHealth * 0.25 + networkHealth * 0.15
                    + skewHealth * 0.15 + throughputHealth * 0.15);
            healthScore.setOverallScore(overall);
            healthScore.setHealthLevel(determineHealthLevel(overall));

            List<String> factors = new ArrayList<>();
            if (cpuHealth < 0.7) factors.add("High CPU usage");
            if (memoryHealth < 0.7) factors.add("High memory pressure");
            if (networkHealth < 0.7) factors.add("Network congestion");
            if (skewHealth < 0.7) factors.add("Data skew detected");
            if (throughputHealth < 0.7) factors.add("Throughput degradation");
            if (factors.isEmpty()) factors.add("All metrics within normal range");
            healthScore.setHealthFactors(factors);

            predictFutureHealth(jobId, healthScore);

        } catch (Exception e) {
            logger.error("Error calculating health for job {}", jobId, e);
            healthScore.setOverallScore(0.0);
            healthScore.setHealthLevel("ERROR");
        }

        return healthScore;
    }

    public List<ResourceWarning> generateWarnings(String jobId) {
        List<ResourceWarning> warnings = new ArrayList<>();
        long now = System.currentTimeMillis();

        try {
            JobTopologyAnalysis analysis = analysisService.analyzeJob(jobId);
            if (analysis == null) {
                return warnings;
            }

            Map<String, Double> utilization = analysis.getResourceUtilization();
            double cpuUtil = utilization.getOrDefault("avgCpuUtilization", 0.0);
            double memoryUtil = utilization.getOrDefault("avgMemoryUtilization", 0.0);
            double networkIn = utilization.getOrDefault("avgNetworkInUtilization", 0.0);
            double networkOut = utilization.getOrDefault("avgNetworkOutUtilization", 0.0);

            if (cpuUtil > CRITICAL_THRESHOLD_CPU) {
                warnings.add(createWarning(jobId, "CPU", "CRITICAL",
                        "CPU utilization critically high", "CPU", cpuUtil, CRITICAL_THRESHOLD_CPU, false, now));
            } else if (cpuUtil > WARNING_THRESHOLD_CPU) {
                warnings.add(createWarning(jobId, "CPU", "WARNING",
                        "CPU utilization approaching limit", "CPU", cpuUtil, WARNING_THRESHOLD_CPU, false, now));
            }

            if (memoryUtil > CRITICAL_THRESHOLD_MEMORY) {
                warnings.add(createWarning(jobId, "MEMORY", "CRITICAL",
                        "Memory utilization critically high, OOM risk", "MEMORY", memoryUtil, CRITICAL_THRESHOLD_MEMORY, false, now));
            } else if (memoryUtil > WARNING_THRESHOLD_MEMORY) {
                warnings.add(createWarning(jobId, "MEMORY", "WARNING",
                        "Memory utilization approaching limit", "MEMORY", memoryUtil, WARNING_THRESHOLD_MEMORY, false, now));
            }

            if (networkIn > WARNING_THRESHOLD_NETWORK || networkOut > WARNING_THRESHOLD_NETWORK) {
                double netUtil = Math.max(networkIn, networkOut);
                warnings.add(createWarning(jobId, "NETWORK", "WARNING",
                        "Network utilization high, may cause bottleneck", "NETWORK", netUtil, WARNING_THRESHOLD_NETWORK, false, now));
            }

            for (JobTopologyAnalysis.VertexAnalysis vertex : analysis.getVertexAnalyses()) {
                if (vertex.getDataSkew() != null && vertex.getDataSkew().getSkewFactor() > SKEW_WARNING_THRESHOLD) {
                    ResourceWarning warning = new ResourceWarning();
                    warning.setWarningId(UUID.randomUUID().toString());
                    warning.setJobId(jobId);
                    warning.setWarningType("DATA_SKEW");
                    warning.setSeverity(vertex.getDataSkew().getSkewFactor() > 0.8 ? "CRITICAL" : "WARNING");
                    warning.setMessage(String.format("Data skew detected in vertex '%s', factor: %.2f",
                            vertex.getVertexName(), vertex.getDataSkew().getSkewFactor()));
                    warning.setResourceType("DATA_DISTRIBUTION");
                    warning.setCurrentValue(vertex.getDataSkew().getSkewFactor());
                    warning.setThreshold(SKEW_WARNING_THRESHOLD);
                    warning.setTimestamp(now);
                    warning.setPrediction(false);
                    warning.getRecommendations().add("Rebalance key distribution");
                    warning.getRecommendations().add("Increase parallelism for this vertex");
                    warning.getRecommendations().add("Consider custom partitioner");
                    warnings.add(warning);
                }
            }

            warnings.addAll(generatePredictiveWarnings(jobId, utilization, now));

            warnings.sort(Comparator.comparingInt(w -> getSeverityOrder(w.getSeverity())));

        } catch (Exception e) {
            logger.error("Error generating warnings for job {}", jobId, e);
        }

        return warnings;
    }

    public Map<String, Object> getHealthDashboard(String jobId) {
        Map<String, Object> dashboard = new HashMap<>();
        dashboard.put("healthScore", calculateJobHealth(jobId));
        dashboard.put("warnings", generateWarnings(jobId));
        dashboard.put("predictionMetrics", getPredictionMetrics(jobId));
        dashboard.put("healthHistory", getHealthHistory(jobId, 7));
        return dashboard;
    }

    private double calculateCpuHealth(Map<String, Double> utilization) {
        double cpu = utilization.getOrDefault("avgCpuUtilization", 0.0);
        if (cpu <= 0.5) return 1.0;
        if (cpu <= 0.7) return 1.0 - (cpu - 0.5) * 1.5;
        if (cpu <= 0.85) return 0.7 - (cpu - 0.7) * 2.0;
        return Math.max(0.0, 0.4 - (cpu - 0.85) * 2.67);
    }

    private double calculateMemoryHealth(Map<String, Double> utilization) {
        double memory = utilization.getOrDefault("avgMemoryUtilization", 0.0);
        if (memory <= 0.5) return 1.0;
        if (memory <= 0.7) return 1.0 - (memory - 0.5) * 1.5;
        if (memory <= 0.85) return 0.7 - (memory - 0.7) * 2.0;
        return Math.max(0.0, 0.4 - (memory - 0.85) * 2.67);
    }

    private double calculateNetworkHealth(Map<String, Double> utilization) {
        double netIn = utilization.getOrDefault("avgNetworkInUtilization", 0.0);
        double netOut = utilization.getOrDefault("avgNetworkOutUtilization", 0.0);
        double net = Math.max(netIn, netOut);
        if (net <= 0.6) return 1.0;
        if (net <= 0.8) return 1.0 - (net - 0.6) * 2.0;
        return Math.max(0.0, 0.6 - (net - 0.8) * 3.0);
    }

    private double calculateSkewHealth(JobTopologyAnalysis analysis) {
        double maxSkew = 0;
        for (JobTopologyAnalysis.VertexAnalysis vertex : analysis.getVertexAnalyses()) {
            if (vertex.getDataSkew() != null && vertex.getDataSkew().isHasSkew()) {
                maxSkew = Math.max(maxSkew, vertex.getDataSkew().getSkewFactor());
            }
        }
        if (maxSkew <= 0.2) return 1.0;
        if (maxSkew <= 0.5) return 1.0 - (maxSkew - 0.2) * 1.33;
        if (maxSkew <= 0.8) return 0.6 - (maxSkew - 0.5) * 1.33;
        return Math.max(0.0, 0.2 - (maxSkew - 0.8));
    }

    private double calculateThroughputHealth(JobTopologyAnalysis analysis) {
        double avgThroughputHealth = 1.0;
        int count = 0;
        for (JobTopologyAnalysis.VertexAnalysis vertex : analysis.getVertexAnalyses()) {
            if (vertex.getSubtaskMetrics() != null && vertex.getSubtaskMetrics().size() > 1) {
                DescriptiveStatistics stats = new DescriptiveStatistics();
                for (JobTopologyAnalysis.SubtaskMetrics subtask : vertex.getSubtaskMetrics()) {
                    stats.addValue(subtask.getBusyRatio());
                }
                double cv = stats.getStandardDeviation() / stats.getMean();
                if (cv <= 0.1) avgThroughputHealth += 1.0;
                else if (cv <= 0.3) avgThroughputHealth += 0.8;
                else if (cv <= 0.5) avgThroughputHealth += 0.6;
                else avgThroughputHealth += 0.4;
                count++;
            }
        }
        return count > 0 ? avgThroughputHealth / count : 1.0;
    }

    private String determineHealthLevel(double score) {
        if (score >= 0.8) return "EXCELLENT";
        if (score >= 0.6) return "GOOD";
        if (score >= 0.4) return "FAIR";
        if (score >= 0.2) return "POOR";
        return "CRITICAL";
    }

    private void predictFutureHealth(String jobId, JobHealthScore healthScore) {
        try {
            List<JobHistoryRecord> history = historicalDataService.getJobHistory(jobId, 30);
            if (history == null || history.size() < MIN_HISTORY_SAMPLES) {
                healthScore.setPredictedScore1h(healthScore.getOverallScore());
                healthScore.setPredictedScore6h(healthScore.getOverallScore());
                healthScore.setPredictedScore24h(healthScore.getOverallScore());
                return;
            }

            List<JobHistoryRecord> recent = history.stream()
                    .sorted(Comparator.comparing(JobHistoryRecord::getRecordedAt).reversed())
                    .limit(10)
                    .collect(Collectors.toList());

            SimpleRegression cpuRegression = new SimpleRegression();
            SimpleRegression memoryRegression = new SimpleRegression();
            long baseTime = recent.get(recent.size() - 1).getRecordedAt().atZone(java.time.ZoneId.systemDefault()).toEpochSecond();

            for (int i = 0; i < recent.size(); i++) {
                JobHistoryRecord record = recent.get(i);
                long time = record.getRecordedAt().atZone(java.time.ZoneId.systemDefault()).toEpochSecond();
                double x = (time - baseTime) / 3600.0;
                cpuRegression.addData(x, record.getAvgCpuUtilization());
                memoryRegression.addData(x, record.getAvgMemoryUtilization());
            }

            double currentScore = healthScore.getOverallScore();
            double cpuSlope = cpuRegression.getSlope();
            double memorySlope = memoryRegression.getSlope();

            double decayFactor = 0.05;
            healthScore.setPredictedScore1h(predictScore(currentScore, cpuSlope, memorySlope, 1, decayFactor));
            healthScore.setPredictedScore6h(predictScore(currentScore, cpuSlope, memorySlope, 6, decayFactor));
            healthScore.setPredictedScore24h(predictScore(currentScore, cpuSlope, memorySlope, 24, decayFactor));

        } catch (Exception e) {
            logger.warn("Could not predict future health for job {}", jobId, e);
            healthScore.setPredictedScore1h(healthScore.getOverallScore());
            healthScore.setPredictedScore6h(healthScore.getOverallScore());
            healthScore.setPredictedScore24h(healthScore.getOverallScore());
        }
    }

    private double predictScore(double currentScore, double cpuSlope, double memorySlope,
                                int hours, double decayFactor) {
        double cpuImpact = Math.max(-0.3, Math.min(0.3, cpuSlope * hours * 0.5));
        double memoryImpact = Math.max(-0.3, Math.min(0.3, memorySlope * hours * 0.5));
        double trendImpact = cpuImpact + memoryImpact;
        double decay = Math.exp(-decayFactor * hours);
        double predicted = currentScore + trendImpact * decay;
        return Math.max(0.0, Math.min(1.0, predicted));
    }

    private List<ResourceWarning> generatePredictiveWarnings(String jobId,
                                                            Map<String, Double> utilization, long now) {
        List<ResourceWarning> warnings = new ArrayList<>();
        try {
            List<JobHistoryRecord> history = historicalDataService.getJobHistory(jobId, 7);
            if (history == null || history.size() < MIN_HISTORY_SAMPLES) {
                return warnings;
            }

            SimpleRegression cpuRegression = new SimpleRegression();
            SimpleRegression memoryRegression = new SimpleRegression();
            long baseTime = System.currentTimeMillis() / 1000;

            for (int i = 0; i < history.size(); i++) {
                JobHistoryRecord record = history.get(i);
                double x = i;
                cpuRegression.addData(x, record.getAvgCpuUtilization());
                memoryRegression.addData(x, record.getAvgMemoryUtilization());
            }

            double currentCpu = utilization.getOrDefault("avgCpuUtilization", 0.0);
            double currentMemory = utilization.getOrDefault("avgMemoryUtilization", 0.0);

            for (int hours : new int[]{1, 6, 24}) {
                double predictedCpu = cpuRegression.predict(hours);
                double predictedMemory = memoryRegression.predict(hours);

                if (predictedCpu > WARNING_THRESHOLD_CPU && currentCpu <= WARNING_THRESHOLD_CPU) {
                    ResourceWarning warning = createWarning(jobId, "CPU", "WARNING",
                            String.format("Predicted CPU will exceed %.0f%% threshold in %d hours (predicted: %.1f%%)",
                                    WARNING_THRESHOLD_CPU * 100, hours, predictedCpu * 100),
                            "CPU", currentCpu, WARNING_THRESHOLD_CPU, true, now);
                    warning.setPredictedValue(predictedCpu);
                    warning.setPredictedTime(now + hours * 3600 * 1000L);
                    warning.getRecommendations().add("Consider scaling out before " + hours + "h");
                    warning.getRecommendations().add("Monitor CPU trends closely");
                    warnings.add(warning);
                    break;
                }
            }

            for (int hours : new int[]{1, 6, 24}) {
                double predictedMemory = memoryRegression.predict(hours);
                if (predictedMemory > WARNING_THRESHOLD_MEMORY && currentMemory <= WARNING_THRESHOLD_MEMORY) {
                    ResourceWarning warning = createWarning(jobId, "MEMORY", "WARNING",
                            String.format("Predicted memory will exceed %.0f%% threshold in %d hours (predicted: %.1f%%)",
                                    WARNING_THRESHOLD_MEMORY * 100, hours, predictedMemory * 100),
                            "MEMORY", currentMemory, WARNING_THRESHOLD_MEMORY, true, now);
                    warning.setPredictedValue(predictedMemory);
                    warning.setPredictedTime(now + hours * 3600 * 1000L);
                    warning.getRecommendations().add("Increase memory allocation before " + hours + "h");
                    warning.getRecommendations().add("Check for memory leaks");
                    warnings.add(warning);
                    break;
                }
            }

        } catch (Exception e) {
            logger.warn("Could not generate predictive warnings for job {}", jobId, e);
        }
        return warnings;
    }

    private ResourceWarning createWarning(String jobId, String warningType, String severity,
                                          String message, String resourceType, double currentValue,
                                          double threshold, boolean isPrediction, long timestamp) {
        ResourceWarning warning = new ResourceWarning();
        warning.setWarningId(UUID.randomUUID().toString());
        warning.setJobId(jobId);
        warning.setWarningType(warningType);
        warning.setSeverity(severity);
        warning.setMessage(message);
        warning.setResourceType(resourceType);
        warning.setCurrentValue(currentValue);
        warning.setThreshold(threshold);
        warning.setTimestamp(timestamp);
        warning.setPrediction(isPrediction);
        return warning;
    }

    private int getSeverityOrder(String severity) {
        return switch (severity) {
            case "CRITICAL" -> 0;
            case "WARNING" -> 1;
            case "INFO" -> 2;
            default -> 3;
        };
    }

    private Map<String, Object> getPredictionMetrics(String jobId) {
        Map<String, Object> metrics = new HashMap<>();
        try {
            List<JobHistoryRecord> history = historicalDataService.getJobHistory(jobId, 30);
            if (history != null && history.size() >= MIN_HISTORY_SAMPLES) {
                SimpleRegression cpuRegression = new SimpleRegression();
                SimpleRegression memoryRegression = new SimpleRegression();

                for (int i = 0; i < history.size(); i++) {
                    JobHistoryRecord record = history.get(i);
                    cpuRegression.addData(i, record.getAvgCpuUtilization());
                    memoryRegression.addData(i, record.getAvgMemoryUtilization());
                }

                metrics.put("cpuTrendSlope", cpuRegression.getSlope());
                metrics.put("cpuTrendRSquare", cpuRegression.getRSquare());
                metrics.put("memoryTrendSlope", memoryRegression.getSlope());
                metrics.put("memoryTrendRSquare", memoryRegression.getRSquare());
                metrics.put("predictionConfidence",
                        (cpuRegression.getRSquare() + memoryRegression.getRSquare()) / 2);
                metrics.put("hasEnoughData", true);
                metrics.put("sampleCount", history.size());
            } else {
                metrics.put("hasEnoughData", false);
                metrics.put("sampleCount", history != null ? history.size() : 0);
            }
        } catch (Exception e) {
            metrics.put("error", e.getMessage());
        }
        return metrics;
    }

    private List<Map<String, Object>> getHealthHistory(String jobId, int days) {
        List<Map<String, Object>> history = new ArrayList<>();
        try {
            List<JobHistoryRecord> records = historicalDataService.getJobHistory(jobId, days);
            if (records != null) {
                for (JobHistoryRecord record : records) {
                    Map<String, Object> entry = new HashMap<>();
                    entry.put("timestamp", record.getRecordedAt().atZone(java.time.ZoneId.systemDefault()).toEpochSecond() * 1000);
                    double cpuHealth = calculateCpuHealth(Map.of("avgCpuUtilization", record.getAvgCpuUtilization()));
                    double memoryHealth = calculateMemoryHealth(Map.of("avgMemoryUtilization", record.getAvgMemoryUtilization()));
                    entry.put("healthScore", (cpuHealth + memoryHealth) / 2);
                    entry.put("cpuUtilization", record.getAvgCpuUtilization());
                    entry.put("memoryUtilization", record.getAvgMemoryUtilization());
                    history.add(entry);
                }
            }
        } catch (Exception e) {
            logger.warn("Could not get health history for job {}", jobId, e);
        }
        return history;
    }
}

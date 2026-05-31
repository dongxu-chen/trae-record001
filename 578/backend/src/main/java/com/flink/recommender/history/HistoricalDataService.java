package com.flink.recommender.history;

import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.VertexAnalysis;
import com.flink.recommender.model.JobHistoryRecord;
import com.flink.recommender.repository.JobHistoryRepository;
import org.apache.commons.math3.stat.regression.SimpleRegression;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class HistoricalDataService {

    private static final Logger logger = LoggerFactory.getLogger(HistoricalDataService.class);

    private final JobHistoryRepository historyRepository;

    public HistoricalDataService(JobHistoryRepository historyRepository) {
        this.historyRepository = historyRepository;
    }

    public void recordJobMetrics(String jobId, JobTopologyAnalysis analysis) {
        logger.info("Recording job metrics for job: {}", jobId);

        double avgCpuUtilization = analysis.getResourceUtilization()
                .getOrDefault("avgCpuUtilization", 50.0);

        @SuppressWarnings("unchecked")
        Map<String, Object> skewAnalysis = analysis.getDataSkewAnalysis();
        boolean hasDataSkew = (Boolean) skewAnalysis.getOrDefault("hasDataSkew", false);
        double dataSkewFactor = 0.0;
        if (hasDataSkew) {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> skewedVertices =
                    (List<Map<String, Object>>) skewAnalysis.getOrDefault("skewedVertices", Collections.emptyList());
            if (!skewedVertices.isEmpty()) {
                dataSkewFactor = (Double) skewedVertices.get(0).getOrDefault("skewFactor", 1.0);
            }
        }

        long totalRecordsProcessed = analysis.getVertexAnalyses().stream()
                .mapToLong(VertexAnalysis::getReadRecords)
                .sum();

        long totalBytesProcessed = analysis.getVertexAnalyses().stream()
                .mapToLong(VertexAnalysis::getReadBytes)
                .sum();

        double avgThroughputRecordsPerSec = analysis.getVertexAnalyses().stream()
                .mapToDouble(VertexAnalysis::getRecordsPerSecond)
                .average()
                .orElse(0.0);

        double avgThroughputBytesPerSec = analysis.getVertexAnalyses().stream()
                .mapToDouble(VertexAnalysis::getBytesPerSecond)
                .average()
                .orElse(0.0);

        JobHistoryRecord record = JobHistoryRecord.builder()
                .jobId(jobId)
                .jobName(analysis.getJobName())
                .parallelism(analysis.getMaxParallelism())
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.0)
                .numTaskManagers(analysis.getTotalVertices())
                .totalRecordsProcessed(totalRecordsProcessed)
                .totalBytesProcessed(totalBytesProcessed)
                .avgThroughputRecordsPerSec(avgThroughputRecordsPerSec)
                .avgThroughputBytesPerSec(avgThroughputBytesPerSec)
                .avgLatencyMs(0.0)
                .avgCpuUtilization(avgCpuUtilization)
                .avgMemoryUtilization(50.0)
                .maxCpuUtilization(avgCpuUtilization * 1.5)
                .maxMemoryUtilization(75.0)
                .hasDataSkew(hasDataSkew)
                .dataSkewFactor(dataSkewFactor)
                .jobDurationMs(analysis.getTotalDuration())
                .succeeded(true)
                .build();

        historyRepository.save(record);
        logger.debug("Job history record saved: jobId={}", jobId);
    }

    public List<JobHistoryRecord> getJobHistory(String jobId) {
        return historyRepository.findByJobIdOrderByRecordedAtDesc(jobId);
    }

    public Optional<JobHistoryRecord> getLatestJobHistory(String jobId) {
        return historyRepository.findFirstByJobIdOrderByRecordedAtDesc(jobId);
    }

    public Map<String, Object> analyzeHistoricalTrends(String jobId) {
        logger.info("Analyzing historical trends for job: {}", jobId);

        List<JobHistoryRecord> history = historyRepository
                .findByJobIdAndRecordedAtAfterOrderByRecordedAtDesc(
                        jobId, LocalDateTime.now().minusDays(30));

        Map<String, Object> trends = new HashMap<>();

        if (history.isEmpty()) {
            trends.put("hasData", false);
            return trends;
        }

        trends.put("hasData", true);
        trends.put("totalRecords", history.size());

        SimpleRegression throughputRegression = new SimpleRegression();
        SimpleRegression latencyRegression = new SimpleRegression();
        SimpleRegression cpuRegression = new SimpleRegression();

        long baseTime = history.get(history.size() - 1).getRecordedAt().getSecond();

        for (int i = 0; i < history.size(); i++) {
            JobHistoryRecord record = history.get(history.size() - 1 - i);
            double timeIndex = record.getRecordedAt().getSecond() - baseTime;

            throughputRegression.addData(timeIndex, record.getAvgThroughputRecordsPerSec());
            latencyRegression.addData(timeIndex, record.getAvgLatencyMs());
            cpuRegression.addData(timeIndex, record.getAvgCpuUtilization());
        }

        trends.put("throughputTrend", interpretTrend(throughputRegression.getSlope()));
        trends.put("throughputSlope", throughputRegression.getSlope());
        trends.put("latencyTrend", interpretTrend(-latencyRegression.getSlope()));
        trends.put("latencySlope", latencyRegression.getSlope());
        trends.put("cpuTrend", interpretTrend(cpuRegression.getSlope()));
        trends.put("cpuSlope", cpuRegression.getSlope());

        double avgThroughput = history.stream()
                .mapToDouble(JobHistoryRecord::getAvgThroughputRecordsPerSec)
                .average()
                .orElse(0.0);

        double avgLatency = history.stream()
                .mapToDouble(JobHistoryRecord::getAvgLatencyMs)
                .average()
                .orElse(0.0);

        double avgCpu = history.stream()
                .mapToDouble(JobHistoryRecord::getAvgCpuUtilization)
                .average()
                .orElse(0.0);

        trends.put("avgThroughput", avgThroughput);
        trends.put("avgLatency", avgLatency);
        trends.put("avgCpuUtilization", avgCpu);

        long skewCount = history.stream()
                .filter(JobHistoryRecord::isHasDataSkew)
                .count();

        trends.put("skewFrequency", (double) skewCount / history.size());
        trends.put("skewCount", skewCount);

        return trends;
    }

    public Map<String, Object> predictResourceNeeds(String jobId, double loadMultiplier) {
        logger.info("Predicting resource needs for job: {}, load multiplier: {}",
                jobId, loadMultiplier);

        Map<String, Object> prediction = new HashMap<>();

        Optional<JobHistoryRecord> latestOpt = historyRepository
                .findFirstByJobIdOrderByRecordedAtDesc(jobId);

        if (latestOpt.isEmpty()) {
            prediction.put("hasPrediction", false);
            return prediction;
        }

        JobHistoryRecord latest = latestOpt.get();
        prediction.put("hasPrediction", true);

        double baseCpu = latest.getAvgCpuUtilization();
        double predictedCpu = Math.min(100, baseCpu * loadMultiplier);

        double requiredParallelism = latest.getParallelism() *
                (predictedCpu / 70.0);

        double predictedMemory = latest.getTaskManagerMemoryMb() *
                Math.max(1, loadMultiplier * 0.5);

        prediction.put("currentParallelism", latest.getParallelism());
        prediction.put("predictedParallelism", (int) Math.ceil(requiredParallelism));
        prediction.put("currentCpuUtilization", baseCpu);
        prediction.put("predictedCpuUtilization", predictedCpu);
        prediction.put("currentMemoryMb", latest.getTaskManagerMemoryMb());
        prediction.put("predictedMemoryMb", (int) Math.ceil(predictedMemory));
        prediction.put("loadMultiplier", loadMultiplier);

        return prediction;
    }

    private String interpretTrend(double slope) {
        if (slope > 10) {
            return "IMPROVING_FAST";
        } else if (slope > 1) {
            return "IMPROVING";
        } else if (slope > -1) {
            return "STABLE";
        } else if (slope > -10) {
            return "DEGRADING";
        } else {
            return "DEGRADING_FAST";
        }
    }

    public List<Map<String, Object>> getResourceEfficiencyReport() {
        logger.info("Generating resource efficiency report");

        List<JobHistoryRecord> allRecords = historyRepository.findAll();

        Map<String, List<JobHistoryRecord>> jobRecords = new HashMap<>();
        for (JobHistoryRecord record : allRecords) {
            jobRecords.computeIfAbsent(record.getJobId(), k -> new ArrayList<>())
                    .add(record);
        }

        List<Map<String, Object>> report = new ArrayList<>();
        for (Map.Entry<String, List<JobHistoryRecord>> entry : jobRecords.entrySet()) {
            Map<String, Object> jobReport = new HashMap<>();
            jobReport.put("jobId", entry.getKey());

            if (!entry.getValue().isEmpty()) {
                JobHistoryRecord latest = entry.getValue().get(0);
                jobReport.put("jobName", latest.getJobName());

                double avgCpu = entry.getValue().stream()
                        .mapToDouble(JobHistoryRecord::getAvgCpuUtilization)
                        .average()
                        .orElse(0.0);

                double efficiencyScore = calculateEfficiencyScore(avgCpu,
                        latest.getTaskManagerMemoryMb(), latest.getParallelism());

                jobReport.put("avgCpuUtilization", avgCpu);
                jobReport.put("efficiencyScore", efficiencyScore);
                jobReport.put("totalExecutions", entry.getValue().size());
                jobReport.put("efficiencyRating", getEfficiencyRating(efficiencyScore));
            }

            report.add(jobReport);
        }

        report.sort((a, b) -> Double.compare(
                (Double) b.getOrDefault("efficiencyScore", 0.0),
                (Double) a.getOrDefault("efficiencyScore", 0.0)));

        return report;
    }

    private double calculateEfficiencyScore(double cpuUtilization, int memoryMb, int parallelism) {
        double cpuScore = 100 - Math.abs(cpuUtilization - 70) * 2;
        double resourceScore = Math.min(100, (1000.0 * parallelism) / memoryMb * 100);
        return (cpuScore * 0.7 + resourceScore * 0.3);
    }

    private String getEfficiencyRating(double score) {
        if (score >= 80) return "EXCELLENT";
        if (score >= 60) return "GOOD";
        if (score >= 40) return "FAIR";
        if (score >= 20) return "POOR";
        return "CRITICAL";
    }
}

package com.flink.recommender.analysis;

import com.flink.recommender.analysis.JobTopologyAnalysis.DataSkewInfo;
import com.flink.recommender.analysis.JobTopologyAnalysis.SubtaskMetrics;
import com.flink.recommender.analysis.JobTopologyAnalysis.VertexAnalysis;
import com.flink.recommender.flink.FlinkRestClient;
import com.flink.recommender.flink.dto.JobDetails;
import com.flink.recommender.flink.dto.JobDetails.Vertex;
import com.flink.recommender.flink.dto.JobOverview;
import com.flink.recommender.flink.dto.VertexDetails;
import com.flink.recommender.flink.dto.VertexDetails.Task;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class JobAnalysisService {

    private static final Logger logger = LoggerFactory.getLogger(JobAnalysisService.class);

    private static final double SKEW_THRESHOLD_HIGH = 2.0;
    private static final double SKEW_THRESHOLD_MEDIUM = 1.5;
    private static final double BOTTLENECK_THRESHOLD = 0.3;

    private final FlinkRestClient flinkRestClient;
    private final DurationCalibrationService durationCalibrationService;
    private final AdvancedDataSkewDetector advancedDataSkewDetector;

    public JobAnalysisService(
            FlinkRestClient flinkRestClient,
            DurationCalibrationService durationCalibrationService,
            AdvancedDataSkewDetector advancedDataSkewDetector) {
        this.flinkRestClient = flinkRestClient;
        this.durationCalibrationService = durationCalibrationService;
        this.advancedDataSkewDetector = advancedDataSkewDetector;
    }

    public List<JobOverview.Job> getAllJobs() {
        return flinkRestClient.getJobOverview()
                .map(JobOverview::getJobs)
                .orElse(Collections.emptyList());
    }

    public Optional<JobTopologyAnalysis> analyzeJob(String jobId) {
        logger.info("Starting analysis for job: {}", jobId);

        Optional<JobDetails> jobDetailsOpt = flinkRestClient.getJobDetails(jobId);
        if (jobDetailsOpt.isEmpty()) {
            logger.warn("Job details not found for job: {}", jobId);
            return Optional.empty();
        }

        JobDetails jobDetails = jobDetailsOpt.get();
        JobTopologyAnalysis analysis = new JobTopologyAnalysis();
        analysis.setJobId(jobDetails.getJobId());
        analysis.setJobName(jobDetails.getName());
        analysis.setTotalDuration(jobDetails.getDuration());
        analysis.setTotalVertices(jobDetails.getVertices().size());
        analysis.setMaxParallelism(jobDetails.getMaxParallelism());

        for (Vertex vertex : jobDetails.getVertices()) {
            VertexAnalysis vertexAnalysis = analyzeVertex(jobId, vertex, jobDetails.getDuration());
            analysis.getVertexAnalyses().add(vertexAnalysis);
        }

        analyzeDataSkew(analysis);
        identifyBottlenecks(analysis);
        calculateResourceUtilization(analysis);
        generateRecommendations(analysis);

        return Optional.of(analysis);
    }

    private VertexAnalysis analyzeVertex(String jobId, Vertex vertex, long totalJobDuration) {
        VertexAnalysis vertexAnalysis = new VertexAnalysis();
        vertexAnalysis.setVertexId(vertex.getId());
        vertexAnalysis.setVertexName(vertex.getName());
        vertexAnalysis.setParallelism(vertex.getParallelism());
        vertexAnalysis.setDuration(vertex.getDuration());

        if (totalJobDuration > 0) {
            vertexAnalysis.setDurationPercentage((double) vertex.getDuration() / totalJobDuration * 100);
        }

        JobDetails.Metrics metrics = vertex.getMetrics();
        long readRecords = 0;
        if (metrics != null) {
            readRecords = metrics.getReadRecords();
            vertexAnalysis.setReadBytes(metrics.getReadBytes());
            vertexAnalysis.setWriteBytes(metrics.getWriteBytes());
            vertexAnalysis.setReadRecords(readRecords);
            vertexAnalysis.setWriteRecords(metrics.getWriteRecords());

            double durationSeconds = vertex.getDuration() / 1000.0;
            if (durationSeconds > 0) {
                vertexAnalysis.setRecordsPerSecond(readRecords / durationSeconds);
                vertexAnalysis.setBytesPerSecond(metrics.getReadBytes() / durationSeconds);
            }

            if (readRecords > 0) {
                vertexAnalysis.setAvgRecordSize((double) metrics.getReadBytes() / readRecords);
            }
        }

        Optional<VertexDetails> vertexDetailsOpt = flinkRestClient.getVertexDetails(jobId, vertex.getId());
        if (vertexDetailsOpt.isPresent()) {
            VertexDetails vertexDetails = vertexDetailsOpt.get();
            for (Task task : vertexDetails.getTasks()) {
                SubtaskMetrics subtaskMetrics = convertToSubtaskMetrics(task);
                vertexAnalysis.getSubtaskMetrics().add(subtaskMetrics);
            }
            vertexAnalysis.setDataSkew(advancedDataSkewDetector.detectDataSkew(vertexDetails.getTasks()));
        }

        DurationCalibrationInfo calibration = durationCalibrationService.calibrateDuration(
                jobId,
                vertex.getName(),
                vertex.getDuration(),
                readRecords,
                vertex.getParallelism());
        vertexAnalysis.setDurationCalibration(calibration);

        long calibratedDuration = durationCalibrationService.applyCalibration(
                vertexAnalysis, calibration);
        vertexAnalysis.setCalibratedDuration(calibratedDuration);

        if (vertexAnalysis.isDurationCalibrated() && totalJobDuration > 0) {
            double calibratedPercentage = (double) calibratedDuration / totalJobDuration * 100;
            logger.debug("Vertex {} duration calibrated: {} -> {} ms ({}%)",
                    vertex.getName(), vertex.getDuration(), calibratedDuration, calibratedPercentage);
        }

        return vertexAnalysis;
    }

    private SubtaskMetrics convertToSubtaskMetrics(Task task) {
        SubtaskMetrics metrics = new SubtaskMetrics();
        metrics.setSubtaskIndex(task.getSubtask());
        metrics.setHost(task.getHost());
        metrics.setDuration(task.getDuration());

        VertexDetails.TaskMetrics taskMetrics = task.getMetrics();
        if (taskMetrics != null) {
            metrics.setReadBytes(taskMetrics.getReadBytes());
            metrics.setWriteBytes(taskMetrics.getWriteBytes());
            metrics.setReadRecords(taskMetrics.getReadRecords());
            metrics.setWriteRecords(taskMetrics.getWriteRecords());
            metrics.setBusyTime(taskMetrics.getBusyTime());
            metrics.setIdleTime(taskMetrics.getIdleTime());
            metrics.setBuffersInPoolUsage(taskMetrics.getBuffersInPoolUsage());
            metrics.setBuffersOutPoolUsage(taskMetrics.getBuffersOutPoolUsage());

            long totalTime = taskMetrics.getBusyTime() + taskMetrics.getIdleTime();
            if (totalTime > 0) {
                metrics.setBusyRatio((double) taskMetrics.getBusyTime() / totalTime);
            }
        }

        return metrics;
    }



    private void analyzeDataSkew(JobTopologyAnalysis analysis) {
        Map<String, Object> skewAnalysis = new HashMap<>();
        List<VertexAnalysis> skewedVertices = analysis.getVertexAnalyses().stream()
                .filter(v -> v.getDataSkew() != null && v.getDataSkew().isHasSkew())
                .collect(Collectors.toList());

        skewAnalysis.put("hasDataSkew", !skewedVertices.isEmpty());
        skewAnalysis.put("skewedVertexCount", skewedVertices.size());
        skewAnalysis.put("skewedVertices", skewedVertices.stream()
                .map(v -> Map.of(
                        "vertexId", v.getVertexId(),
                        "vertexName", v.getVertexName(),
                        "skewFactor", v.getDataSkew().getSkewFactor(),
                        "severity", v.getDataSkew().getSeverity()
                ))
                .collect(Collectors.toList()));

        analysis.setDataSkewAnalysis(skewAnalysis);
    }

    private void identifyBottlenecks(JobTopologyAnalysis analysis) {
        List<String> bottlenecks = new ArrayList<>();

        for (VertexAnalysis vertex : analysis.getVertexAnalyses()) {
            if (vertex.getDurationPercentage() >= BOTTLENECK_THRESHOLD * 100) {
                vertex.setBottleneck(true);
                bottlenecks.add(String.format("Vertex '%s' is a bottleneck (%.1f%% of total job time)",
                        vertex.getVertexName(), vertex.getDurationPercentage()));
            }

            if (vertex.getDataSkew() != null && vertex.getDataSkew().isHasSkew()) {
                bottlenecks.add(String.format("Vertex '%s' has data skew (factor: %.2f, severity: %s)",
                        vertex.getVertexName(),
                        vertex.getDataSkew().getSkewFactor(),
                        vertex.getDataSkew().getSeverity()));
            }
        }

        analysis.setBottlenecks(bottlenecks);
    }

    private void calculateResourceUtilization(JobTopologyAnalysis analysis) {
        Map<String, Double> utilization = new HashMap<>();

        double avgBusyRatio = analysis.getVertexAnalyses().stream()
                .flatMap(v -> v.getSubtaskMetrics().stream())
                .mapToDouble(SubtaskMetrics::getBusyRatio)
                .average()
                .orElse(0.0);

        double avgBuffersInUsage = analysis.getVertexAnalyses().stream()
                .flatMap(v -> v.getSubtaskMetrics().stream())
                .mapToDouble(SubtaskMetrics::getBuffersInPoolUsage)
                .average()
                .orElse(0.0);

        double avgBuffersOutUsage = analysis.getVertexAnalyses().stream()
                .flatMap(v -> v.getSubtaskMetrics().stream())
                .mapToDouble(SubtaskMetrics::getBuffersOutPoolUsage)
                .average()
                .orElse(0.0);

        utilization.put("avgCpuUtilization", avgBusyRatio * 100);
        utilization.put("avgNetworkInUtilization", avgBuffersInUsage * 100);
        utilization.put("avgNetworkOutUtilization", avgBuffersOutUsage * 100);

        analysis.setResourceUtilization(utilization);
    }

    private void generateRecommendations(JobTopologyAnalysis analysis) {
        List<String> recommendations = new ArrayList<>();

        for (VertexAnalysis vertex : analysis.getVertexAnalyses()) {
            if (vertex.isBottleneck()) {
                recommendations.add(String.format(
                        "Consider increasing parallelism for bottleneck vertex '%s' (current: %d)",
                        vertex.getVertexName(), vertex.getParallelism()));
            }

            DataSkewInfo dataSkew = vertex.getDataSkew();
            if (dataSkew != null && dataSkew.isHasSkew()) {
                recommendations.add(String.format(
                        "Address data skew in vertex '%s': consider re-partitioning or using key salting (skew factor: %.2f)",
                        vertex.getVertexName(), dataSkew.getSkewFactor()));
            }
        }

        analysis.setRecommendations(recommendations);
    }
}

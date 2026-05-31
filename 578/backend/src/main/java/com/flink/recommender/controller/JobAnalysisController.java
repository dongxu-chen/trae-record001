package com.flink.recommender.controller;

import com.flink.recommender.analysis.AdvancedDataSkewDetector;
import com.flink.recommender.analysis.DurationCalibrationService;
import com.flink.recommender.analysis.JobAnalysisService;
import com.flink.recommender.analysis.JobTopologyAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.*;
import com.flink.recommender.flink.dto.JobOverview;
import com.flink.recommender.history.HistoricalDataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/jobs")
@CrossOrigin(origins = "http://localhost:3000")
public class JobAnalysisController {

    private static final Logger logger = LoggerFactory.getLogger(JobAnalysisController.class);

    private final JobAnalysisService jobAnalysisService;
    private final HistoricalDataService historicalDataService;
    private final DurationCalibrationService durationCalibrationService;
    private final AdvancedDataSkewDetector advancedDataSkewDetector;

    public JobAnalysisController(
            JobAnalysisService jobAnalysisService,
            HistoricalDataService historicalDataService,
            DurationCalibrationService durationCalibrationService,
            AdvancedDataSkewDetector advancedDataSkewDetector) {
        this.jobAnalysisService = jobAnalysisService;
        this.historicalDataService = historicalDataService;
        this.durationCalibrationService = durationCalibrationService;
        this.advancedDataSkewDetector = advancedDataSkewDetector;
    }

    @GetMapping
    public ResponseEntity<List<JobOverview.Job>> getAllJobs() {
        logger.info("Getting all jobs");
        List<JobOverview.Job> jobs = jobAnalysisService.getAllJobs();
        return ResponseEntity.ok(jobs);
    }

    @GetMapping("/{jobId}/analyze")
    public ResponseEntity<?> analyzeJob(@PathVariable String jobId) {
        logger.info("Analyzing job: {}", jobId);

        Optional<JobTopologyAnalysis> analysisOpt = jobAnalysisService.analyzeJob(jobId);

        if (analysisOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        JobTopologyAnalysis analysis = analysisOpt.get();

        try {
            historicalDataService.recordJobMetrics(jobId, analysis);
        } catch (Exception e) {
            logger.warn("Failed to record job metrics: {}", e.getMessage());
        }

        return ResponseEntity.ok(analysis);
    }

    @GetMapping("/{jobId}/history")
    public ResponseEntity<?> getJobHistory(@PathVariable String jobId) {
        logger.info("Getting job history for: {}", jobId);
        return ResponseEntity.ok(historicalDataService.getJobHistory(jobId));
    }

    @GetMapping("/{jobId}/trends")
    public ResponseEntity<?> getJobTrends(@PathVariable String jobId) {
        logger.info("Getting job trends for: {}", jobId);
        return ResponseEntity.ok(historicalDataService.analyzeHistoricalTrends(jobId));
    }

    @GetMapping("/{jobId}/predict")
    public ResponseEntity<?> predictResourceNeeds(
            @PathVariable String jobId,
            @RequestParam(defaultValue = "1.0") double loadMultiplier) {
        logger.info("Predicting resource needs for job: {}, load multiplier: {}",
                jobId, loadMultiplier);
        return ResponseEntity.ok(historicalDataService.predictResourceNeeds(jobId, loadMultiplier));
    }

    @GetMapping("/efficiency-report")
    public ResponseEntity<?> getEfficiencyReport() {
        logger.info("Generating efficiency report");
        return ResponseEntity.ok(historicalDataService.getResourceEfficiencyReport());
    }

    @GetMapping("/{jobId}/calibration-report")
    public ResponseEntity<?> getCalibrationReport(@PathVariable String jobId) {
        logger.info("Getting duration calibration report for job: {}", jobId);
        Map<String, Object> report = durationCalibrationService.getCalibrationReport(jobId);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/{jobId}/skew-detection-report")
    public ResponseEntity<?> getSkewDetectionReport(
            @PathVariable String jobId,
            @RequestParam(defaultValue = "Window Aggregation") String vertexName) {
        logger.info("Getting skew detection report for job: {}, vertex: {}", jobId, vertexName);
        Map<String, Object> report = advancedDataSkewDetector.getSkewDetectionReport(vertexName);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/demo/mock-analysis")
    public ResponseEntity<?> getMockAnalysis() {
        logger.info("Generating mock analysis for demo");

        JobTopologyAnalysis analysis = new JobTopologyAnalysis();
        analysis.setJobId("demo-job-" + System.currentTimeMillis());
        analysis.setJobName("Demo Streaming Job");
        analysis.setTotalDuration(3600000);
        analysis.setTotalVertices(4);
        analysis.setMaxParallelism(128);

        for (int i = 0; i < 4; i++) {
            VertexAnalysis vertex = new VertexAnalysis();
            vertex.setVertexId("vertex-" + i);
            vertex.setVertexName(getVertexName(i));
            vertex.setParallelism(8);
            vertex.setDuration(900000 + i * 100000);
            vertex.setDurationPercentage(25 + i * 5);
            vertex.setReadBytes(1000000000L + i * 100000000L);
            vertex.setWriteBytes(500000000L + i * 50000000L);
            vertex.setReadRecords(10000000L + i * 1000000L);
            vertex.setWriteRecords(5000000L + i * 500000L);
            vertex.setRecordsPerSecond(10000 + i * 1000);
            vertex.setBytesPerSecond(1000000 + i * 100000);
            vertex.setAvgRecordSize(100 + i * 10);
            vertex.setBottleneck(i == 2);

            DurationCalibrationInfo calibration = new DurationCalibrationInfo();
            calibration.setHistoricalAvgDuration(950000L + i * 50000);
            calibration.setHistoricalMedianDuration(920000L + i * 45000);
            calibration.setHistoricalP95Duration(1100000L + i * 60000);
            calibration.setHistoricalMinDuration(800000L + i * 30000);
            calibration.setHistoricalMaxDuration(1200000L + i * 80000);
            calibration.setDurationStdDev(85000 + i * 5000);
            calibration.setHistoricalSampleCount(15 + i * 3);
            calibration.setConfidenceLevel(0.75 + i * 0.05);
            calibration.setCalibrationFactor(0.95 + i * 0.02);
            calibration.setCalibrationMethod(i == 0 ? "HISTORICAL_MEAN" : i == 1 ? "REGRESSION_BASED" : "LOAD_ADJUSTED_MEAN");
            calibration.getCalibrationReasons().add("Duration is consistent with historical patterns");
            if (i == 2) {
                calibration.getCalibrationReasons().add("Bottleneck vertex requires additional calibration");
            }
            vertex.setDurationCalibration(calibration);
            vertex.setCalibratedDuration((long) (vertex.getDuration() * calibration.getCalibrationFactor()));
            vertex.setCalibrationError(3.5 + i * 0.8);
            vertex.setDurationCalibrated(true);

            DataSkewInfo skewInfo = new DataSkewInfo();
            skewInfo.setHasSkew(i == 1);
            skewInfo.setSkewFactor(i == 1 ? 2.5 : 1.0);
            skewInfo.setMaxRecords(1000000);
            skewInfo.setMinRecords(100000);
            skewInfo.setAvgRecords(500000);
            skewInfo.setStdDevRecords(300000);
            skewInfo.setCoefficientOfVariation(i == 1 ? 0.6 : 0.1);
            skewInfo.setSeverity(i == 1 ? "HIGH" : "LOW");
            skewInfo.setFullKeyScanEnabled(true);
            skewInfo.setSamplingVerified(i == 1);
            skewInfo.setTotalUniqueKeys(50000 + i * 10000);
            skewInfo.setSampledKeys(5000 + i * 500);
            skewInfo.setSamplingRate(0.1);
            skewInfo.setDetectionConfidence(i == 1 ? 0.92 : 0.85);
            if (i == 1) {
                skewInfo.getSkewedSubtasks().add(3);
                skewInfo.getSkewedSubtasks().add(7);

                KeyDistributionAnalysis keyDist = new KeyDistributionAnalysis();
                keyDist.setTotalKeysAnalyzed(500000);
                keyDist.setSampledKeyCount(25000);
                keyDist.setGiniCoefficient(0.55);
                keyDist.setEntropy(0.72);
                keyDist.setTop1KeyPercentage(18.5);
                keyDist.setTop5KeysPercentage(42.3);
                keyDist.setTop10KeysPercentage(58.7);
                keyDist.setDistributionPattern("EXTREME_SKEW");

                List<KeyFrequencyBin> bins = new ArrayList<>();
                bins.add(createBin("Hot (>50%)", 3, 185000, 18.5));
                bins.add(createBin("Warm (20-50%)", 12, 238000, 23.8));
                bins.add(createBin("Normal (5-20%)", 245, 402500, 40.25));
                bins.add(createBin("Cold (1-5%)", 1250, 147000, 14.7));
                bins.add(createBin("Very Cold (<1%)", 23490, 27500, 2.75));
                keyDist.setFrequencyDistribution(bins);
                skewInfo.setKeyDistribution(keyDist);

                List<HotKeyInfo> hotKeys = new ArrayList<>();
                hotKeys.add(createHotKey("hot_key_0", 92500, 18.5, 3, true, "HOT"));
                hotKeys.add(createHotKey("hot_key_1", 45000, 9.0, 3, true, "HOT"));
                hotKeys.add(createHotKey("hot_key_2", 32000, 6.4, 7, true, "HOT"));
                hotKeys.add(createHotKey("hot_key_5", 28000, 5.6, 7, true, "HOT"));
                hotKeys.add(createHotKey("hot_key_3", 22000, 4.4, 3, false, "WARM"));
                skewInfo.setHotKeys(hotKeys);
            }
            vertex.setDataSkew(skewInfo);

            for (int j = 0; j < 8; j++) {
                SubtaskMetrics subtask = new SubtaskMetrics();
                subtask.setSubtaskIndex(j);
                subtask.setHost("taskmanager-" + (j % 2));
                subtask.setDuration(900000);
                subtask.setReadBytes(125000000 + j * 1000000);
                subtask.setWriteBytes(62500000 + j * 500000);
                subtask.setReadRecords(1250000 + j * 10000);
                subtask.setWriteRecords(625000 + j * 5000);
                subtask.setBusyTime(630000);
                subtask.setIdleTime(270000);
                subtask.setBusyRatio(0.7);
                subtask.setBuffersInPoolUsage(0.3 + j * 0.05);
                subtask.setBuffersOutPoolUsage(0.25 + j * 0.03);
                vertex.getSubtaskMetrics().add(subtask);
            }

            analysis.getVertexAnalyses().add(vertex);
        }

        Map<String, Object> skewAnalysis = new HashMap<>();
        skewAnalysis.put("hasDataSkew", true);
        skewAnalysis.put("skewedVertexCount", 1);
        skewAnalysis.put("skewedVertices", List.of(
                Map.of("vertexId", "vertex-1",
                        "vertexName", "Window Aggregation",
                        "skewFactor", 2.5,
                        "severity", "HIGH")
        ));
        analysis.setDataSkewAnalysis(skewAnalysis);

        Map<String, Double> utilization = new HashMap<>();
        utilization.put("avgCpuUtilization", 70.0);
        utilization.put("avgNetworkInUtilization", 35.0);
        utilization.put("avgNetworkOutUtilization", 28.0);
        analysis.setResourceUtilization(utilization);

        analysis.getBottlenecks().add("Vertex 'Keyed Process' is a bottleneck (35.0% of total job time)");
        analysis.getBottlenecks().add("Vertex 'Window Aggregation' has data skew (factor: 2.50, severity: HIGH)");

        analysis.getRecommendations().add("Consider increasing parallelism for bottleneck vertex 'Keyed Process' (current: 8)");
        analysis.getRecommendations().add("Address data skew in vertex 'Window Aggregation': consider re-partitioning or using key salting");

        return ResponseEntity.ok(analysis);
    }

    private String getVertexName(int index) {
        return switch (index) {
            case 0 -> "Source: Kafka Consumer";
            case 1 -> "Window Aggregation";
            case 2 -> "Keyed Process";
            case 3 -> "Sink: Elasticsearch";
            default -> "Unknown Vertex";
        };
    }

    private KeyFrequencyBin createBin(String range, long keyCount, long recordCount, double percentage) {
        KeyFrequencyBin bin = new KeyFrequencyBin();
        bin.setRange(range);
        bin.setKeyCount(keyCount);
        bin.setRecordCount(recordCount);
        bin.setPercentage(percentage);
        return bin;
    }

    private HotKeyInfo createHotKey(String keyHash, long count, double percentage,
                                    int subtaskIndex, boolean verified, String keyType) {
        HotKeyInfo hotKey = new HotKeyInfo();
        hotKey.setKeyHash(keyHash);
        hotKey.setCount(count);
        hotKey.setPercentage(percentage);
        hotKey.setSubtaskIndex(subtaskIndex);
        hotKey.setVerifiedBySampling(verified);
        hotKey.setKeyType(keyType);
        return hotKey;
    }
}

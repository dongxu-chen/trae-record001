package com.flink.recommender.analysis;

import com.flink.recommender.analysis.JobTopologyAnalysis.DurationCalibrationInfo;
import com.flink.recommender.analysis.JobTopologyAnalysis.VertexAnalysis;
import com.flink.recommender.model.JobHistoryRecord;
import com.flink.recommender.repository.JobHistoryRepository;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.apache.commons.math3.stat.regression.SimpleRegression;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class DurationCalibrationService {

    private static final Logger logger = LoggerFactory.getLogger(DurationCalibrationService.class);

    private static final int MIN_HISTORICAL_SAMPLES = 3;
    private static final int MAX_HISTORICAL_SAMPLES = 50;
    private static final double OUTLIER_THRESHOLD = 3.0;
    private static final double MIN_CONFIDENCE_FOR_CALIBRATION = 0.6;

    private final JobHistoryRepository historyRepository;

    public DurationCalibrationService(JobHistoryRepository historyRepository) {
        this.historyRepository = historyRepository;
    }

    public DurationCalibrationInfo calibrateDuration(
            String jobId,
            String vertexName,
            long currentDuration,
            long currentRecords,
            int currentParallelism) {

        logger.debug("Calibrating duration for job: {}, vertex: {}", jobId, vertexName);

        DurationCalibrationInfo calibration = new DurationCalibrationInfo();

        List<JobHistoryRecord> historicalRecords = historyRepository
                .findByJobIdAndRecordedAtAfterOrderByRecordedAtDesc(
                        jobId, LocalDateTime.now().minusDays(30));

        if (historicalRecords.size() < MIN_HISTORICAL_SAMPLES) {
            calibration.setHistoricalSampleCount(historicalRecords.size());
            calibration.setConfidenceLevel(0.3);
            calibration.setCalibrationMethod("INSUFFICIENT_DATA");
            calibration.getCalibrationReasons().add("Insufficient historical data for calibration");
            return calibration;
        }

        List<Long> historicalDurations = new ArrayList<>();
        List<Long> historicalRecordsCounts = new ArrayList<>();
        List<Integer> historicalParallelisms = new ArrayList<>();

        for (JobHistoryRecord record : historicalRecords) {
            if (record.getJobDurationMs() > 0) {
                historicalDurations.add(record.getJobDurationMs());
                historicalRecordsCounts.add(record.getTotalRecordsProcessed());
                historicalParallelisms.add(record.getParallelism());
            }
        }

        if (historicalDurations.size() < MIN_HISTORICAL_SAMPLES) {
            calibration.setHistoricalSampleCount(historicalDurations.size());
            calibration.setConfidenceLevel(0.4);
            calibration.setCalibrationMethod("INSUFFICIENT_VALID_DATA");
            calibration.getCalibrationReasons().add("Insufficient valid historical duration data");
            return calibration;
        }

        DescriptiveStatistics stats = removeOutliers(historicalDurations);

        calibration.setHistoricalSampleCount((int) stats.getN());
        calibration.setHistoricalAvgDuration((long) stats.getMean());
        calibration.setHistoricalMedianDuration((long) stats.getPercentile(50));
        calibration.setHistoricalP95Duration((long) stats.getPercentile(95));
        calibration.setHistoricalMinDuration((long) stats.getMin());
        calibration.setHistoricalMaxDuration((long) stats.getMax());
        calibration.setDurationStdDev(stats.getStandardDeviation());

        double coefficientOfVariation = stats.getMean() > 0
                ? stats.getStandardDeviation() / stats.getMean()
                : 0;

        double baseConfidence = calculateConfidenceLevel(
                stats.getN(), coefficientOfVariation, currentRecords);

        calibration.setConfidenceLevel(baseConfidence);

        double calibrationFactor = calculateCalibrationFactor(
                currentDuration,
                currentRecords,
                currentParallelism,
                stats,
                historicalRecordsCounts,
                historicalParallelisms);

        calibration.setCalibrationFactor(calibrationFactor);

        String calibrationMethod = determineCalibrationMethod(
                coefficientOfVariation,
                baseConfidence,
                historicalRecordsCounts,
                historicalParallelisms);

        calibration.setCalibrationMethod(calibrationMethod);

        List<String> reasons = generateCalibrationReasons(
                currentDuration,
                stats,
                coefficientOfVariation,
                calibrationFactor,
                currentRecords,
                currentParallelism,
                historicalRecordsCounts,
                historicalParallelisms);
        calibration.getCalibrationReasons().addAll(reasons);

        return calibration;
    }

    private DescriptiveStatistics removeOutliers(List<Long> values) {
        DescriptiveStatistics stats = new DescriptiveStatistics();

        double mean = values.stream().mapToLong(Long::longValue).average().orElse(0);
        double stdDev = calculateStdDev(values, mean);

        if (stdDev == 0) {
            for (Long value : values) {
                stats.addValue(value);
            }
            return stats;
        }

        for (Long value : values) {
            double zScore = Math.abs((value - mean) / stdDev);
            if (zScore <= OUTLIER_THRESHOLD) {
                stats.addValue(value);
            } else {
                logger.debug("Removed outlier duration: {}", value);
            }
        }

        return stats;
    }

    private double calculateStdDev(List<Long> values, double mean) {
        if (values.size() < 2) return 0;

        double sumSquaredDiff = 0;
        for (Long value : values) {
            sumSquaredDiff += Math.pow(value - mean, 2);
        }

        return Math.sqrt(sumSquaredDiff / (values.size() - 1));
    }

    private double calculateConfidenceLevel(
            long sampleCount,
            double coefficientOfVariation,
            long currentRecords) {

        double sampleConfidence = Math.min(1.0, (double) sampleCount / 20.0);
        double varianceConfidence = Math.max(0, 1.0 - coefficientOfVariation * 2);
        double dataConfidence = Math.min(1.0, currentRecords / 1000000.0);

        return (sampleConfidence * 0.4 + varianceConfidence * 0.4 + dataConfidence * 0.2);
    }

    private double calculateCalibrationFactor(
            long currentDuration,
            long currentRecords,
            int currentParallelism,
            DescriptiveStatistics historicalStats,
            List<Long> historicalRecordsCounts,
            List<Integer> historicalParallelisms) {

        if (historicalStats.getN() == 0) {
            return 1.0;
        }

        double historicalAvgDuration = historicalStats.getMean();
        double historicalAvgRecords = historicalRecordsCounts.stream()
                .mapToLong(Long::longValue)
                .average()
                .orElse(1.0);
        double historicalAvgParallelism = historicalParallelisms.stream()
                .mapToInt(Integer::intValue)
                .average()
                .orElse(1.0);

        double recordsRatio = historicalAvgRecords > 0
                ? (double) currentRecords / historicalAvgRecords
                : 1.0;

        double parallelismRatio = historicalAvgParallelism > 0
                ? historicalAvgParallelism / currentParallelism
                : 1.0;

        double loadFactor = Math.max(0.3, Math.min(3.0, recordsRatio * parallelismRatio));

        double regressionFactor = calculateRegressionFactor(
                currentRecords, currentParallelism,
                historicalRecordsCounts, historicalParallelisms,
                new ArrayList<>(historicalStats.getValues()));

        double simpleFactor = historicalAvgDuration / Math.max(1, currentDuration);

        if (regressionFactor > 0) {
            return simpleFactor * 0.3 + regressionFactor * 0.7;
        }

        return simpleFactor * loadFactor;
    }

    private double calculateRegressionFactor(
            long currentRecords,
            int currentParallelism,
            List<Long> historicalRecords,
            List<Integer> historicalParallelism,
            List<Double> historicalDurations) {

        if (historicalDurations.size() < 5) {
            return -1;
        }

        SimpleRegression regression = new SimpleRegression();

        for (int i = 0; i < historicalDurations.size() && i < historicalRecords.size(); i++) {
            double records = historicalRecords.get(i);
            double duration = historicalDurations.get(i);
            if (records > 0 && duration > 0) {
                double normalizedLoad = records / Math.max(1, historicalParallelism.get(i));
                regression.addData(normalizedLoad, duration);
            }
        }

        if (regression.getR() < 0.5) {
            return -1;
        }

        double currentNormalizedLoad = (double) currentRecords / Math.max(1, currentParallelism);
        double predictedDuration = regression.predict(currentNormalizedLoad);

        return predictedDuration > 0 ? 1.0 : -1;
    }

    private String determineCalibrationMethod(
            double coefficientOfVariation,
            double confidence,
            List<Long> historicalRecords,
            List<Integer> historicalParallelisms) {

        if (coefficientOfVariation < 0.1 && confidence > 0.8) {
            return "HISTORICAL_MEAN";
        } else if (coefficientOfVariation < 0.3 && confidence > 0.6) {
            return "LOAD_ADJUSTED_MEAN";
        } else if (confidence > 0.5) {
            return "REGRESSION_BASED";
        } else {
            return "MEDIAN_BASED";
        }
    }

    private List<String> generateCalibrationReasons(
            long currentDuration,
            DescriptiveStatistics stats,
            double coefficientOfVariation,
            double calibrationFactor,
            long currentRecords,
            int currentParallelism,
            List<Long> historicalRecords,
            List<Integer> historicalParallelisms) {

        List<String> reasons = new ArrayList<>();

        double historicalAvg = stats.getMean();
        double deviationPercent = historicalAvg > 0
                ? Math.abs(currentDuration - historicalAvg) / historicalAvg * 100
                : 0;

        if (deviationPercent > 20) {
            reasons.add(String.format(
                    "Current duration deviates %.1f%% from historical average",
                    deviationPercent));
        }

        if (coefficientOfVariation > 0.3) {
            reasons.add(String.format(
                    "High variability in historical durations (CV: %.2f)",
                    coefficientOfVariation));
        }

        double avgHistoricalRecords = historicalRecords.stream()
                .mapToLong(Long::longValue)
                .average()
                .orElse(0);

        if (avgHistoricalRecords > 0) {
            double recordRatio = (double) currentRecords / avgHistoricalRecords;
            if (recordRatio > 1.5 || recordRatio < 0.5) {
                reasons.add(String.format(
                        "Current data volume is %.1fx of historical average",
                        recordRatio));
            }
        }

        double avgHistoricalParallelism = historicalParallelisms.stream()
                .mapToInt(Integer::intValue)
                .average()
                .orElse(1);

        if (avgHistoricalParallelism > 0) {
            double parallelismRatio = (double) currentParallelism / avgHistoricalParallelism;
            if (parallelismRatio > 1.5 || parallelismRatio < 0.5) {
                reasons.add(String.format(
                        "Current parallelism is %.1fx of historical average",
                        parallelismRatio));
            }
        }

        if (calibrationFactor != 1.0) {
            reasons.add(String.format(
                    "Applied calibration factor of %.3f",
                    calibrationFactor));
        }

        if (reasons.isEmpty()) {
            reasons.add("Duration is consistent with historical patterns");
        }

        return reasons;
    }

    public long applyCalibration(VertexAnalysis vertex, DurationCalibrationInfo calibration) {
        if (calibration.getConfidenceLevel() < MIN_CONFIDENCE_FOR_CALIBRATION) {
            return vertex.getDuration();
        }

        long baseDuration = switch (calibration.getCalibrationMethod()) {
            case "HISTORICAL_MEAN" -> calibration.getHistoricalAvgDuration();
            case "MEDIAN_BASED" -> calibration.getHistoricalMedianDuration();
            case "P95_BASED" -> calibration.getHistoricalP95Duration();
            default -> calibration.getHistoricalAvgDuration();
        };

        long calibratedDuration = (long) (baseDuration * calibration.getCalibrationFactor());

        double error = Math.abs(calibratedDuration - vertex.getDuration()) /
                (double) Math.max(1, vertex.getDuration()) * 100;

        vertex.setCalibrationError(error);
        vertex.setDurationCalibrated(true);

        return calibratedDuration;
    }

    public Map<String, Object> getCalibrationReport(String jobId) {
        Map<String, Object> report = new HashMap<>();

        List<JobHistoryRecord> history = historyRepository
                .findTop10ByJobIdOrderByRecordedAtDesc(jobId);

        report.put("jobId", jobId);
        report.put("historicalSamples", history.size());

        if (!history.isEmpty()) {
            DescriptiveStatistics durationStats = new DescriptiveStatistics();
            DescriptiveStatistics throughputStats = new DescriptiveStatistics();

            for (JobHistoryRecord record : history) {
                if (record.getJobDurationMs() > 0) {
                    durationStats.addValue(record.getJobDurationMs());
                }
                if (record.getAvgThroughputRecordsPerSec() > 0) {
                    throughputStats.addValue(record.getAvgThroughputRecordsPerSec());
                }
            }

            report.put("duration", Map.of(
                    "avg", durationStats.getMean(),
                    "median", durationStats.getPercentile(50),
                    "p95", durationStats.getPercentile(95),
                    "min", durationStats.getMin(),
                    "max", durationStats.getMax(),
                    "stdDev", durationStats.getStandardDeviation(),
                    "cv", durationStats.getMean() > 0
                            ? durationStats.getStandardDeviation() / durationStats.getMean()
                            : 0
            ));

            report.put("throughput", Map.of(
                    "avg", throughputStats.getMean(),
                    "median", throughputStats.getPercentile(50),
                    "p95", throughputStats.getPercentile(95)
            ));

            double cv = durationStats.getMean() > 0
                    ? durationStats.getStandardDeviation() / durationStats.getMean()
                    : 0;

            report.put("calibrationQuality", cv < 0.1 ? "EXCELLENT"
                    : cv < 0.3 ? "GOOD"
                    : cv < 0.5 ? "FAIR" : "POOR");
        }

        return report;
    }
}

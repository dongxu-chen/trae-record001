package com.health.task.service;

import com.health.task.dto.PredictionResponse;
import com.health.task.entity.HealthScore;
import com.health.task.entity.HealthScorePrediction;
import com.health.task.model.TaskMetrics;
import com.health.task.repository.HealthScorePredictionRepository;
import com.health.task.repository.HealthScoreRepository;
import com.health.task.repository.TaskExecutionRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class HealthScorePredictionService {

    private final HealthScoreRepository healthScoreRepo;
    private final HealthScorePredictionRepository predictionRepo;
    private final TaskExecutionRecordRepository executionRepo;
    private final HealthScoringService scoringService;

    private static final int DEFAULT_PREDICTION_HOURS = 72;
    private static final int PREDICTION_INTERVAL_HOURS = 6;

    public PredictionResponse predictHealthScore(String taskName, String taskGroup, Integer horizonHours) {
        int horizon = horizonHours != null ? horizonHours : DEFAULT_PREDICTION_HOURS;

        List<HealthScore> historicalScores = healthScoreRepo
                .findByTaskNameOrderByCalculatedAtDesc(taskName)
                .stream()
                .limit(30)
                .toList();

        if (historicalScores.isEmpty()) {
            return buildEmptyPrediction(taskName, taskGroup);
        }

        double[] scores = historicalScores.stream()
                .mapToInt(HealthScore::getOverallScore)
                .asDoubleStream()
                .toArray();

        double[] times = new double[scores.length];
        for (int i = 0; i < scores.length; i++) {
            times[i] = scores.length - i;
        }

        RegressionResult regression = linearRegression(times, scores);
        String trendDirection = regression.slope > 0.5 ? "IMPROVING" :
                regression.slope < -0.5 ? "DECLINING" : "STABLE";

        List<PredictionResponse.PredictedScorePoint> predictedPoints = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();
        int currentScore = historicalScores.get(0).getOverallScore();

        TaskMetrics metrics = scoringService.collectMetrics(taskName, taskGroup,
                now.minusHours(24), now);

        double volatility = calculateVolatility(scores);
        double baseConfidence = calculateConfidence(scores.length, volatility);

        for (int i = 0; i <= horizon; i += PREDICTION_INTERVAL_HOURS) {
            if (i == 0) continue;

            LocalDateTime targetTime = now.plusHours(i);
            double predictedValue = regression.intercept + regression.slope * (scores.length + (double) i / PREDICTION_INTERVAL_HOURS);
            predictedValue = applyMetricsAdjustment(predictedValue, metrics);

            int predictedScore = (int) Math.max(0, Math.min(100, predictedValue));
            double confidence = Math.max(0.3, baseConfidence - (double) i / horizon * 0.4);
            int stdDev = (int) (volatility * 1.5);
            int lowerBound = Math.max(0, predictedScore - stdDev);
            int upperBound = Math.min(100, predictedScore + stdDev);

            predictedPoints.add(PredictionResponse.PredictedScorePoint.builder()
                    .time(targetTime)
                    .predictedScore(predictedScore)
                    .lowerBound(lowerBound)
                    .upperBound(upperBound)
                    .confidence(confidence)
                    .build());

            savePrediction(taskName, taskGroup, predictedScore, confidence,
                    trendDirection, regression.slope, now, targetTime,
                    i, "LINEAR_REGRESSION", lowerBound, upperBound);
        }

        String summary = generateForecastSummary(currentScore, predictedPoints, trendDirection, metrics);

        return PredictionResponse.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .currentScore(currentScore)
                .predictedScores(predictedPoints)
                .trendDirection(trendDirection)
                .trendSlope(Math.round(regression.slope * 100.0) / 100.0)
                .confidence(Math.round(baseConfidence * 100.0) / 100.0)
                .algorithmUsed("LINEAR_REGRESSION_WITH_METRICS_ADJUSTMENT")
                .predictionTime(now)
                .predictionHorizonHours(horizon)
                .forecastSummary(summary)
                .build();
    }

    private double applyMetricsAdjustment(double predictedScore, TaskMetrics metrics) {
        double adjustment = 0;

        if (metrics.getSuccessRate() < 80) {
            adjustment -= 5;
        } else if (metrics.getSuccessRate() > 95) {
            adjustment += 2;
        }

        if (metrics.getAvgDurationMs() > 10000) {
            adjustment -= 3;
        }

        if (metrics.getAvgCpuUsage() > 80) {
            adjustment -= 2;
        }

        if (metrics.getExecutionCount() < 5) {
            adjustment -= 3;
        }

        return predictedScore + adjustment;
    }

    private RegressionResult linearRegression(double[] x, double[] y) {
        int n = x.length;
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            sumX += x[i];
            sumY += y[i];
            sumXY += x[i] * y[i];
            sumX2 += x[i] * x[i];
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        double intercept = (sumY - slope * sumX) / n;

        return new RegressionResult(slope, intercept);
    }

    private double calculateVolatility(double[] scores) {
        if (scores.length < 2) return 5.0;
        double mean = 0;
        for (double s : scores) mean += s;
        mean /= scores.length;

        double variance = 0;
        for (double s : scores) variance += (s - mean) * (s - mean);
        return Math.sqrt(variance / scores.length);
    }

    private double calculateConfidence(int dataPoints, double volatility) {
        double dataFactor = Math.min(1.0, (double) dataPoints / 20);
        double volatilityFactor = Math.max(0.5, 1 - volatility / 30);
        return dataFactor * volatilityFactor;
    }

    private String generateForecastSummary(int currentScore,
                                            List<PredictionResponse.PredictedScorePoint> points,
                                            String trend, TaskMetrics metrics) {
        if (points.isEmpty()) return "Insufficient data for prediction";

        int finalScore = points.get(points.size() - 1).getPredictedScore();
        int scoreChange = finalScore - currentScore;

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Current score: %d. ", currentScore));

        if ("IMPROVING".equals(trend)) {
            sb.append("Trend is improving. ");
        } else if ("DECLINING".equals(trend)) {
            sb.append("Trend is declining. ");
        } else {
            sb.append("Trend is stable. ");
        }

        if (scoreChange > 5) {
            sb.append(String.format("Expected to improve to %d in %d hours. ", finalScore,
                    (int) java.time.Duration.between(LocalDateTime.now(),
                            points.get(points.size() - 1).getTime()).toHours()));
        } else if (scoreChange < -5) {
            sb.append(String.format("Expected to decline to %d in %d hours. ", finalScore,
                    (int) java.time.Duration.between(LocalDateTime.now(),
                            points.get(points.size() - 1).getTime()).toHours()));
        } else {
            sb.append(String.format("Expected to remain stable around %d. ", finalScore));
        }

        if (metrics.getSuccessRate() < 80) {
            sb.append("Warning: Low success rate may impact future scores.");
        } else if (metrics.getAvgDurationMs() > 10000) {
            sb.append("Warning: High execution duration detected.");
        }

        return sb.toString();
    }

    private void savePrediction(String taskName, String taskGroup, int predictedScore,
                                double confidence, String trendDirection, double trendSlope,
                                LocalDateTime predictionTime, LocalDateTime targetTime,
                                int horizon, String algorithm, int lowerBound, int upperBound) {
        try {
            HealthScorePrediction prediction = HealthScorePrediction.builder()
                    .taskName(taskName)
                    .taskGroup(taskGroup)
                    .predictedScore(predictedScore)
                    .confidence(confidence)
                    .trendDirection(trendDirection)
                    .trendSlope(trendSlope)
                    .predictionTime(predictionTime)
                    .targetTime(targetTime)
                    .predictionHorizonHours(horizon)
                    .algorithmUsed(algorithm)
                    .lowerBound(lowerBound)
                    .upperBound(upperBound)
                    .build();
            predictionRepo.save(prediction);
        } catch (Exception e) {
            log.warn("Failed to save prediction for {}: {}", taskName, e.getMessage());
        }
    }

    private PredictionResponse buildEmptyPrediction(String taskName, String taskGroup) {
        return PredictionResponse.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .currentScore(null)
                .predictedScores(new ArrayList<>())
                .trendDirection("UNKNOWN")
                .trendSlope(0.0)
                .confidence(0.0)
                .algorithmUsed("NONE")
                .predictionTime(LocalDateTime.now())
                .predictionHorizonHours(DEFAULT_PREDICTION_HOURS)
                .forecastSummary("Insufficient historical data for prediction. Please wait for more scoring cycles.")
                .build();
    }

    public List<HealthScorePrediction> getPredictionHistory(String taskName, LocalDateTime since) {
        if (since != null) {
            return predictionRepo.findByTaskNameAndPredictionTimeAfterOrderByPredictionTimeDesc(taskName, since);
        }
        return predictionRepo.findByTaskNameOrderByPredictionTimeDesc(taskName);
    }

    private static class RegressionResult {
        final double slope;
        final double intercept;

        RegressionResult(double slope, double intercept) {
            this.slope = slope;
            this.intercept = intercept;
        }
    }
}

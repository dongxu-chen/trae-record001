package com.mqmonitor.prediction;

import com.mqmonitor.common.config.PredictionConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.PredictionResult;
import com.mqmonitor.common.model.TimeSeriesPoint;
import com.mqmonitor.common.util.StatsUtil;
import com.mqmonitor.common.util.TimeWindow;
import com.mqmonitor.collector.MetricsManager;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class TimeSeriesPredictor {
    private static final Logger logger = LoggerFactory.getLogger(TimeSeriesPredictor.class);

    private final MetricsManager metricsManager;
    private final PredictionConfig config;

    public TimeSeriesPredictor(PredictionConfig config) {
        this.metricsManager = MetricsManager.getInstance();
        this.config = config;
    }

    public PredictionResult predictBacklog(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = buildKey(clusterName, topic, consumerGroup);
        TimeWindow<Double> historyWindow = metricsManager.getCollectorService().getBacklogHistoryMap().get(key);

        if (historyWindow == null || historyWindow.size() < config.getMinDataPointsForPrediction()) {
            logger.warn("Insufficient data points for prediction on {}. Need {}, have {}",
                    key, config.getMinDataPointsForPrediction(),
                    historyWindow != null ? historyWindow.size() : 0);
            return null;
        }

        List<Double> historicalData = historyWindow.getValues();
        List<Double> smoothedData = smoothData(historicalData, config.getSmoothingWindowSize());

        StatsUtil.BurstDetectionResult burstResult = detectBurst(historicalData);

        PredictionResult result = switch (config.getDefaultAlgorithm().toUpperCase()) {
            case "HOLT_WINTERS" -> holtWintersPredict(mqType, clusterName, topic, consumerGroup, smoothedData);
            case "ARIMA" -> arimaPredict(mqType, clusterName, topic, consumerGroup, smoothedData);
            case "LINEAR_REGRESSION" -> linearRegressionPredict(mqType, clusterName, topic, consumerGroup, smoothedData);
            default -> linearRegressionPredict(mqType, clusterName, topic, consumerGroup, smoothedData);
        };

        if (result != null && burstResult != null && burstResult.isBurst()) {
            applyBurstAdjustment(result, burstResult, historicalData);
        }

        return result;
    }

    private StatsUtil.BurstDetectionResult detectBurst(List<Double> historicalData) {
        int burstWindowSize = Math.min(5, historicalData.size() / 4);
        return StatsUtil.detectBurst(historicalData, burstWindowSize, 2.0);
    }

    private void applyBurstAdjustment(PredictionResult result, StatsUtil.BurstDetectionResult burstResult,
                                   List<Double> historicalData) {
        result.setBurstDetected(true);
        result.setBurstMagnitude(burstResult.getBurstMagnitude());
        result.setBurstScore(burstResult.getBurstScore());
        result.setBurstAdjustmentFactor(burstResult.getAdjustmentFactor());
        result.setBurstDetectedAt(System.currentTimeMillis());

        List<Double> originalValues = new ArrayList<>(result.getPredictedValues());
        result.setOriginalPredictedValues(originalValues);

        List<Double> adjustedValues = new ArrayList<>();
        double factor = burstResult.getAdjustmentFactor();
        for (int i = 0; i < originalValues.size(); i++) {
            double decayFactor = Math.max(0.3, 1.0 - (double) i / originalValues.size());
            double adjustedValue = originalValues.get(i) * (1 + (factor - 1) * decayFactor);
            adjustedValues.add(Math.max(0, adjustedValue));
        }

        result.setPredictedValues(adjustedValues);

        long adjustedAtHorizon = adjustedValues.get(adjustedValues.size() - 1).longValue();
        result.setPredictedBacklogAtHorizon(adjustedAtHorizon);
        result.setWillExceedThreshold(adjustedAtHorizon > config.getBacklogWarningThreshold());

        logger.info("Burst detected for {}: magnitude={}, factor={}, originalHorizon={}, adjustedHorizon={}",
                result.getTopic(), burstResult.getBurstMagnitude(), factor,
                originalValues.get(originalValues.size() - 1).longValue(), adjustedAtHorizon);
    }

    private PredictionResult linearRegressionPredict(MQType mqType, String clusterName, String topic,
                                                     String consumerGroup, List<Double> data) {
        int horizon = config.getPredictionHorizonMinutes();

        double[] regression = StatsUtil.linearRegression(data);
        double slope = regression[0];
        double intercept = regression[1];

        List<Double> predictedValues = new ArrayList<>();
        List<Long> timestamps = new ArrayList<>();
        long now = Instant.now().toEpochMilli();
        long intervalMs = 60000;

        for (int i = 1; i <= horizon; i++) {
            double predicted = slope * (data.size() + i) + intercept;
            predicted = Math.max(0, predicted);
            predictedValues.add(predicted);
            timestamps.add(now + i * intervalMs);
        }

        double growthRate = slope;
        long lastValue = data.get(data.size() - 1).longValue();
        long predictedAtHorizon = predictedValues.get(predictedValues.size() - 1).longValue();

        double confidence = calculateConfidence(data, predictedValues);
        boolean willExceed = predictedAtHorizon > config.getBacklogWarningThreshold();

        PredictionResult result = new PredictionResult();
        result.setMqType(mqType);
        result.setClusterName(clusterName);
        result.setTopic(topic);
        result.setConsumerGroup(consumerGroup);
        result.setPredictionHorizonMinutes(horizon);
        result.setPredictedValues(predictedValues);
        result.setPredictionTimestamps(timestamps);
        result.setAlgorithm("LINEAR_REGRESSION");
        result.setGrowthRate(growthRate);
        result.setPredictedBacklogAtHorizon(predictedAtHorizon);
        result.setWillExceedThreshold(willExceed);
        result.setThreshold(config.getBacklogWarningThreshold());
        result.setConfidence(confidence);

        return result;
    }

    private PredictionResult holtWintersPredict(MQType mqType, String clusterName, String topic,
                                                String consumerGroup, List<Double> data) {
        int horizon = config.getPredictionHorizonMinutes();
        double alpha = 0.3;
        double beta = 0.1;
        double gamma = 0.1;
        int seasonLength = 12;

        List<Double> level = new ArrayList<>();
        List<Double> trend = new ArrayList<>();
        List<Double> seasonal = new ArrayList<>();

        double initialLevel = data.subList(0, Math.min(seasonLength, data.size())).stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElse(0);
        level.add(initialLevel);

        double initialTrend = 0;
        for (int i = 0; i < Math.min(seasonLength, data.size() - 1); i++) {
            initialTrend += (data.get(i + 1) - data.get(i)) / seasonLength;
        }
        trend.add(initialTrend);

        for (int i = 0; i < Math.min(seasonLength, data.size()); i++) {
            seasonal.add(data.get(i) / initialLevel);
        }

        for (int i = 1; i < data.size(); i++) {
            double currentLevel = alpha * (data.get(i) / seasonal.get(i % seasonLength)) + (1 - alpha) * (level.get(i - 1) + trend.get(i - 1));
            double currentTrend = beta * (currentLevel - level.get(i - 1)) + (1 - beta) * trend.get(i - 1);
            double currentSeasonal = gamma * (data.get(i) / currentLevel) + (1 - gamma) * seasonal.get(i % seasonLength);

            level.add(currentLevel);
            trend.add(currentTrend);
            seasonal.set(i % seasonLength, currentSeasonal);
        }

        List<Double> predictedValues = new ArrayList<>();
        List<Long> timestamps = new ArrayList<>();
        long now = Instant.now().toEpochMilli();
        long intervalMs = 60000;

        double lastLevel = level.get(level.size() - 1);
        double lastTrend = trend.get(trend.size() - 1);

        for (int i = 1; i <= horizon; i++) {
            int seasonIdx = (data.size() + i - 1) % seasonLength;
            double predicted = (lastLevel + i * lastTrend) * seasonal.get(seasonIdx);
            predicted = Math.max(0, predicted);
            predictedValues.add(predicted);
            timestamps.add(now + i * intervalMs);
        }

        double growthRate = StatsUtil.calculateGrowthRate(data);
        long predictedAtHorizon = predictedValues.get(predictedValues.size() - 1).longValue();
        double confidence = calculateConfidence(data, predictedValues);
        boolean willExceed = predictedAtHorizon > config.getBacklogWarningThreshold();

        PredictionResult result = new PredictionResult();
        result.setMqType(mqType);
        result.setClusterName(clusterName);
        result.setTopic(topic);
        result.setConsumerGroup(consumerGroup);
        result.setPredictionHorizonMinutes(horizon);
        result.setPredictedValues(predictedValues);
        result.setPredictionTimestamps(timestamps);
        result.setAlgorithm("HOLT_WINTERS");
        result.setGrowthRate(growthRate);
        result.setPredictedBacklogAtHorizon(predictedAtHorizon);
        result.setWillExceedThreshold(willExceed);
        result.setThreshold(config.getBacklogWarningThreshold());
        result.setConfidence(confidence);

        return result;
    }

    private PredictionResult arimaPredict(MQType mqType, String clusterName, String topic,
                                          String consumerGroup, List<Double> data) {
        int horizon = config.getPredictionHorizonMinutes();
        int p = 1, d = 1, q = 1;

        List<Double> differenced = new ArrayList<>();
        for (int i = 1; i < data.size(); i++) {
            differenced.add(data.get(i) - data.get(i - 1));
        }

        double mean = StatsUtil.mean(differenced);
        double variance = StatsUtil.standardDeviation(differenced);

        List<Double> predictedDifferenced = new ArrayList<>();
        for (int i = 0; i < horizon; i++) {
            double ar = !differenced.isEmpty() ? differenced.get(differenced.size() - 1) * 0.5 : 0;
            double ma = mean;
            double pred = ar + ma + (Math.random() - 0.5) * variance * 0.1;
            predictedDifferenced.add(pred);
            differenced.add(pred);
        }

        List<Double> predictedValues = new ArrayList<>();
        List<Long> timestamps = new ArrayList<>();
        long now = Instant.now().toEpochMilli();
        long intervalMs = 60000;
        double lastValue = data.get(data.size() - 1);

        for (int i = 0; i < horizon; i++) {
            lastValue += predictedDifferenced.get(i);
            lastValue = Math.max(0, lastValue);
            predictedValues.add(lastValue);
            timestamps.add(now + (i + 1) * intervalMs);
        }

        double growthRate = StatsUtil.calculateGrowthRate(data);
        long predictedAtHorizon = predictedValues.get(predictedValues.size() - 1).longValue();
        double confidence = calculateConfidence(data, predictedValues);
        boolean willExceed = predictedAtHorizon > config.getBacklogWarningThreshold();

        PredictionResult result = new PredictionResult();
        result.setMqType(mqType);
        result.setClusterName(clusterName);
        result.setTopic(topic);
        result.setConsumerGroup(consumerGroup);
        result.setPredictionHorizonMinutes(horizon);
        result.setPredictedValues(predictedValues);
        result.setPredictionTimestamps(timestamps);
        result.setAlgorithm("ARIMA(" + p + "," + d + "," + q + ")");
        result.setGrowthRate(growthRate);
        result.setPredictedBacklogAtHorizon(predictedAtHorizon);
        result.setWillExceedThreshold(willExceed);
        result.setThreshold(config.getBacklogWarningThreshold());
        result.setConfidence(confidence);

        return result;
    }

    private List<Double> smoothData(List<Double> data, int windowSize) {
        if (windowSize <= 1 || data.size() <= windowSize) {
            return new ArrayList<>(data);
        }

        List<Double> smoothed = new ArrayList<>();
        DescriptiveStatistics stats = new DescriptiveStatistics(windowSize);

        for (int i = 0; i < data.size(); i++) {
            stats.addValue(data.get(i));
            if (i >= windowSize - 1) {
                smoothed.add(stats.getMean());
            } else {
                smoothed.add(data.get(i));
            }
        }

        return smoothed;
    }

    private double calculateConfidence(List<Double> data, List<Double> predictions) {
        double std = StatsUtil.standardDeviation(data);
        double meanPred = StatsUtil.mean(predictions);
        if (meanPred == 0) return 0.0;
        double cv = std / meanPred;
        return Math.max(0, Math.min(1, 1 - cv * 0.5));
    }

    private String buildKey(String clusterName, String topic, String consumerGroup) {
        return clusterName + ":" + topic + (consumerGroup != null ? ":" + consumerGroup : "");
    }

    public List<TimeSeriesPoint> getHistoricalBacklog(String clusterName, String topic, String consumerGroup,
                                                      long startTime, long endTime) {
        return metricsManager.getBacklogHistory(clusterName, topic, consumerGroup, startTime, endTime);
    }

    public PredictionConfig getConfig() {
        return config;
    }
}

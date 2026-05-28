package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.List;

public class PredictionResult {
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String consumerGroup;
    private long predictionTime;
    private int predictionHorizonMinutes;
    private List<Double> predictedValues;
    private List<Long> predictionTimestamps;
    private double confidence;
    private String algorithm;
    private double growthRate;
    private long predictedBacklogAtHorizon;
    private boolean willExceedThreshold;
    private long threshold;
    private boolean burstDetected;
    private double burstMagnitude;
    private double burstScore;
    private double burstAdjustmentFactor;
    private List<Double> originalPredictedValues;
    private long burstDetectedAt;

    public PredictionResult() {
        this.predictionTime = Instant.now().toEpochMilli();
    }

    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public long getPredictionTime() { return predictionTime; }
    public void setPredictionTime(long predictionTime) { this.predictionTime = predictionTime; }
    public int getPredictionHorizonMinutes() { return predictionHorizonMinutes; }
    public void setPredictionHorizonMinutes(int predictionHorizonMinutes) { this.predictionHorizonMinutes = predictionHorizonMinutes; }
    public List<Double> getPredictedValues() { return predictedValues; }
    public void setPredictedValues(List<Double> predictedValues) { this.predictedValues = predictedValues; }
    public List<Long> getPredictionTimestamps() { return predictionTimestamps; }
    public void setPredictionTimestamps(List<Long> predictionTimestamps) { this.predictionTimestamps = predictionTimestamps; }
    public double getConfidence() { return confidence; }
    public void setConfidence(double confidence) { this.confidence = confidence; }
    public String getAlgorithm() { return algorithm; }
    public void setAlgorithm(String algorithm) { this.algorithm = algorithm; }
    public double getGrowthRate() { return growthRate; }
    public void setGrowthRate(double growthRate) { this.growthRate = growthRate; }
    public long getPredictedBacklogAtHorizon() { return predictedBacklogAtHorizon; }
    public void setPredictedBacklogAtHorizon(long predictedBacklogAtHorizon) { this.predictedBacklogAtHorizon = predictedBacklogAtHorizon; }
    public boolean isWillExceedThreshold() { return willExceedThreshold; }
    public void setWillExceedThreshold(boolean willExceedThreshold) { this.willExceedThreshold = willExceedThreshold; }
    public long getThreshold() { return threshold; }
    public void setThreshold(long threshold) { this.threshold = threshold; }
    public boolean isBurstDetected() { return burstDetected; }
    public void setBurstDetected(boolean burstDetected) { this.burstDetected = burstDetected; }
    public double getBurstMagnitude() { return burstMagnitude; }
    public void setBurstMagnitude(double burstMagnitude) { this.burstMagnitude = burstMagnitude; }
    public double getBurstScore() { return burstScore; }
    public void setBurstScore(double burstScore) { this.burstScore = burstScore; }
    public double getBurstAdjustmentFactor() { return burstAdjustmentFactor; }
    public void setBurstAdjustmentFactor(double burstAdjustmentFactor) { this.burstAdjustmentFactor = burstAdjustmentFactor; }
    public List<Double> getOriginalPredictedValues() { return originalPredictedValues; }
    public void setOriginalPredictedValues(List<Double> originalPredictedValues) { this.originalPredictedValues = originalPredictedValues; }
    public long getBurstDetectedAt() { return burstDetectedAt; }
    public void setBurstDetectedAt(long burstDetectedAt) { this.burstDetectedAt = burstDetectedAt; }
}

package com.mqmonitor.common.config;

public class PredictionConfig {
    private int predictionHorizonMinutes = 30;
    private int minDataPointsForPrediction = 30;
    private int smoothingWindowSize = 5;
    private String defaultAlgorithm = "HOLT_WINTERS";
    private double confidenceLevel = 0.95;
    private long backlogWarningThreshold = 10000;
    private long backlogCriticalThreshold = 50000;

    public int getPredictionHorizonMinutes() { return predictionHorizonMinutes; }
    public void setPredictionHorizonMinutes(int predictionHorizonMinutes) { this.predictionHorizonMinutes = predictionHorizonMinutes; }
    public int getMinDataPointsForPrediction() { return minDataPointsForPrediction; }
    public void setMinDataPointsForPrediction(int minDataPointsForPrediction) { this.minDataPointsForPrediction = minDataPointsForPrediction; }
    public int getSmoothingWindowSize() { return smoothingWindowSize; }
    public void setSmoothingWindowSize(int smoothingWindowSize) { this.smoothingWindowSize = smoothingWindowSize; }
    public String getDefaultAlgorithm() { return defaultAlgorithm; }
    public void setDefaultAlgorithm(String defaultAlgorithm) { this.defaultAlgorithm = defaultAlgorithm; }
    public double getConfidenceLevel() { return confidenceLevel; }
    public void setConfidenceLevel(double confidenceLevel) { this.confidenceLevel = confidenceLevel; }
    public long getBacklogWarningThreshold() { return backlogWarningThreshold; }
    public void setBacklogWarningThreshold(long backlogWarningThreshold) { this.backlogWarningThreshold = backlogWarningThreshold; }
    public long getBacklogCriticalThreshold() { return backlogCriticalThreshold; }
    public void setBacklogCriticalThreshold(long backlogCriticalThreshold) { this.backlogCriticalThreshold = backlogCriticalThreshold; }
}

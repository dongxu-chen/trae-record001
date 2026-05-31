package com.distributed.lock.analysis;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class LockWaitPredictor {

    private static final Logger logger = LoggerFactory.getLogger(LockWaitPredictor.class);
    private static final int MIN_SAMPLES_FOR_PREDICTION = 10;
    private static final double EWMA_ALPHA = 0.3;

    private final LockAnalysisService analysisService;

    public LockWaitPredictor(LockAnalysisService analysisService) {
        this.analysisService = analysisService;
    }

    public WaitPrediction predictWaitTime(String lockKey) {
        LockAnalysisService.LockStatistics stats = analysisService.getLockStatisticsMap().get(lockKey);

        WaitPrediction prediction = new WaitPrediction();
        prediction.setLockKey(lockKey);

        if (stats == null || stats.getAcquireCount() < MIN_SAMPLES_FOR_PREDICTION) {
            prediction.setPredicted(false);
            prediction.setReason(stats == null ? "No statistics available for this lock"
                    : String.format("Insufficient samples (%d < %d)", stats.getAcquireCount(), MIN_SAMPLES_FOR_PREDICTION));
            prediction.setEstimatedWaitTimeMs(0);
            prediction.setConfidence(0);
            return prediction;
        }

        prediction.setPredicted(true);

        List<Long> recentWaitTimes = stats.getRecentWaitTimes(100);
        List<Long> recentHoldTimes = stats.getRecentHoldTimes(100);

        double ewmaWait = calculateEWMA(recentWaitTimes);
        double medianWait = calculatePercentile(recentWaitTimes, 50);
        double p90Wait = calculatePercentile(recentWaitTimes, 90);
        double p95Wait = calculatePercentile(recentWaitTimes, 95);

        double avgHoldTime = stats.getAvgHoldTimeMs();
        double contentionRate = stats.getContentionRate();
        int activeHolders = stats.getActiveHolderCount();

        double predictedWait = combinePrediction(ewmaWait, medianWait, p90Wait, contentionRate, activeHolders, avgHoldTime);

        prediction.setEstimatedWaitTimeMs(Math.max(0, (long) predictedWait));
        prediction.setConfidence(calculateConfidence(stats, recentWaitTimes));

        prediction.setEwmaWaitMs((long) ewmaWait);
        prediction.setMedianWaitMs((long) medianWait);
        prediction.setP90WaitMs((long) p90Wait);
        prediction.setP95WaitMs((long) p95Wait);

        prediction.setContentionRate(contentionRate);
        prediction.setActiveHolders(activeHolders);
        prediction.setAvgHoldTimeMs((long) avgHoldTime);

        prediction.setAcquireProbability(calculateAcquireProbability(stats, predictedWait));

        return prediction;
    }

    public Map<String, WaitPrediction> predictAllLocks() {
        Map<String, WaitPrediction> predictions = new HashMap<>();
        for (String lockKey : analysisService.getLockStatisticsMap().keySet()) {
            predictions.put(lockKey, predictWaitTime(lockKey));
        }
        return predictions;
    }

    private double calculateEWMA(List<Long> values) {
        if (values.isEmpty()) {
            return 0;
        }

        double ewma = values.get(0);
        for (int i = 1; i < values.size(); i++) {
            ewma = EWMA_ALPHA * values.get(i) + (1 - EWMA_ALPHA) * ewma;
        }
        return ewma;
    }

    private double calculatePercentile(List<Long> values, double percentile) {
        if (values.isEmpty()) {
            return 0;
        }
        List<Long> sorted = new ArrayList<>(values);
        sorted.sort(Long::compare);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    private double combinePrediction(double ewma, double median, double p90,
                                     double contentionRate, int activeHolders, double avgHoldTime) {
        double baseWait = ewma * 0.3 + median * 0.3 + p90 * 0.4;

        double contentionMultiplier = 1.0 + contentionRate * 2.0;

        double holderMultiplier = 1.0 + Math.max(0, activeHolders - 1) * 0.5;

        double queuingEstimate = activeHolders > 0 ? avgHoldTime * (activeHolders - 1) * 0.3 : 0;

        double predicted = baseWait * contentionMultiplier * holderMultiplier + queuingEstimate;

        return Math.max(0, predicted);
    }

    private double calculateConfidence(LockAnalysisService.LockStatistics stats, List<Long> recentWaitTimes) {
        double confidence = 1.0;

        if (stats.getAcquireCount() < 50) {
            confidence *= 0.5;
        } else if (stats.getAcquireCount() < 200) {
            confidence *= 0.75;
        }

        if (!recentWaitTimes.isEmpty()) {
            double avg = recentWaitTimes.stream().mapToLong(l -> l).average().orElse(0);
            double variance = recentWaitTimes.stream()
                    .mapToDouble(l -> Math.pow(l - avg, 2))
                    .average().orElse(0);
            double stdDev = Math.sqrt(variance);
            double cv = avg > 0 ? stdDev / avg : 0;

            if (cv > 2.0) {
                confidence *= 0.4;
            } else if (cv > 1.0) {
                confidence *= 0.6;
            } else if (cv > 0.5) {
                confidence *= 0.8;
            }
        }

        return Math.min(1.0, Math.max(0, confidence));
    }

    private double calculateAcquireProbability(LockAnalysisService.LockStatistics stats, double predictedWait) {
        double successRate = 1.0 - stats.getContentionRate();

        if (predictedWait <= 0) {
            return successRate;
        }

        double avgWait = stats.getAvgWaitTimeMs();
        if (avgWait <= 0) {
            return successRate;
        }

        double waitRatio = predictedWait / avgWait;
        if (waitRatio < 1.0) {
            return Math.min(0.99, successRate * 1.1);
        } else if (waitRatio < 2.0) {
            return successRate;
        } else if (waitRatio < 5.0) {
            return successRate * 0.7;
        } else {
            return successRate * 0.3;
        }
    }

    public static class WaitPrediction {
        private String lockKey;
        private boolean predicted;
        private String reason;
        private long estimatedWaitTimeMs;
        private double confidence;
        private long ewmaWaitMs;
        private long medianWaitMs;
        private long p90WaitMs;
        private long p95WaitMs;
        private double contentionRate;
        private int activeHolders;
        private long avgHoldTimeMs;
        private double acquireProbability;

        public String getLockKey() {
            return lockKey;
        }

        public void setLockKey(String lockKey) {
            this.lockKey = lockKey;
        }

        public boolean isPredicted() {
            return predicted;
        }

        public void setPredicted(boolean predicted) {
            this.predicted = predicted;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }

        public long getEstimatedWaitTimeMs() {
            return estimatedWaitTimeMs;
        }

        public void setEstimatedWaitTimeMs(long estimatedWaitTimeMs) {
            this.estimatedWaitTimeMs = estimatedWaitTimeMs;
        }

        public double getConfidence() {
            return confidence;
        }

        public void setConfidence(double confidence) {
            this.confidence = confidence;
        }

        public long getEwmaWaitMs() {
            return ewmaWaitMs;
        }

        public void setEwmaWaitMs(long ewmaWaitMs) {
            this.ewmaWaitMs = ewmaWaitMs;
        }

        public long getMedianWaitMs() {
            return medianWaitMs;
        }

        public void setMedianWaitMs(long medianWaitMs) {
            this.medianWaitMs = medianWaitMs;
        }

        public long getP90WaitMs() {
            return p90WaitMs;
        }

        public void setP90WaitMs(long p90WaitMs) {
            this.p90WaitMs = p90WaitMs;
        }

        public long getP95WaitMs() {
            return p95WaitMs;
        }

        public void setP95WaitMs(long p95WaitMs) {
            this.p95WaitMs = p95WaitMs;
        }

        public double getContentionRate() {
            return contentionRate;
        }

        public void setContentionRate(double contentionRate) {
            this.contentionRate = contentionRate;
        }

        public int getActiveHolders() {
            return activeHolders;
        }

        public void setActiveHolders(int activeHolders) {
            this.activeHolders = activeHolders;
        }

        public long getAvgHoldTimeMs() {
            return avgHoldTimeMs;
        }

        public void setAvgHoldTimeMs(long avgHoldTimeMs) {
            this.avgHoldTimeMs = avgHoldTimeMs;
        }

        public double getAcquireProbability() {
            return acquireProbability;
        }

        public void setAcquireProbability(double acquireProbability) {
            this.acquireProbability = acquireProbability;
        }
    }
}
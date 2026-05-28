package com.mqmonitor.common.util;

import org.apache.commons.math3.distribution.NormalDistribution;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;

import java.util.List;

public class StatsUtil {

    private StatsUtil() {}

    public static double mean(List<Double> values) {
        if (values == null || values.isEmpty()) return 0.0;
        DescriptiveStatistics stats = new DescriptiveStatistics();
        values.forEach(stats::addValue);
        return stats.getMean();
    }

    public static double standardDeviation(List<Double> values) {
        if (values == null || values.size() < 2) return 0.0;
        DescriptiveStatistics stats = new DescriptiveStatistics();
        values.forEach(stats::addValue);
        return stats.getStandardDeviation();
    }

    public static double zScore(double value, List<Double> values) {
        double mean = mean(values);
        double std = standardDeviation(values);
        if (std == 0) return 0.0;
        return (value - mean) / std;
    }

    public static double percentile(List<Double> values, double p) {
        if (values == null || values.isEmpty()) return 0.0;
        DescriptiveStatistics stats = new DescriptiveStatistics();
        values.forEach(stats::addValue);
        return stats.getPercentile(p);
    }

    public static double max(List<Double> values) {
        if (values == null || values.isEmpty()) return 0.0;
        DescriptiveStatistics stats = new DescriptiveStatistics();
        values.forEach(stats::addValue);
        return stats.getMax();
    }

    public static double min(List<Double> values) {
        if (values == null || values.isEmpty()) return 0.0;
        DescriptiveStatistics stats = new DescriptiveStatistics();
        values.forEach(stats::addValue);
        return stats.getMin();
    }

    public static boolean isAnomaly(double value, List<Double> historicalValues, double zScoreThreshold) {
        double z = Math.abs(zScore(value, historicalValues));
        return z > zScoreThreshold;
    }

    public static double calculateGrowthRate(List<Double> values) {
        if (values == null || values.size() < 2) return 0.0;
        int n = values.size();
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            double x = i;
            double y = values.get(i);
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        return slope;
    }

    public static double exponentialSmoothing(List<Double> values, double alpha) {
        if (values == null || values.isEmpty()) return 0.0;
        double result = values.get(0);
        for (int i = 1; i < values.size(); i++) {
            result = alpha * values.get(i) + (1 - alpha) * result;
        }
        return result;
    }

    public static double[] linearRegression(List<Double> values) {
        if (values == null || values.size() < 2) return new double[]{0, 0};
        int n = values.size();
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            double x = i;
            double y = values.get(i);
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        double intercept = (sumY - slope * sumX) / n;
        return new double[]{slope, intercept};
    }

    public static double confidenceIntervalWidth(List<Double> values, double confidenceLevel) {
        if (values == null || values.size() < 2) return 0.0;
        double std = standardDeviation(values);
        int n = values.size();
        NormalDistribution nd = new NormalDistribution(0, 1);
        double z = nd.inverseCumulativeProbability(1 - (1 - confidenceLevel) / 2);
        return z * std / Math.sqrt(n);
    }

    public static class BurstDetectionResult {
        private final boolean isBurst;
        private final double burstMagnitude;
        private final double burstScore;
        private final double baselineMean;
        private final double baselineStd;
        private final double adjustmentFactor;

        public BurstDetectionResult(boolean isBurst, double burstMagnitude, double burstScore,
                                    double baselineMean, double baselineStd) {
            this.isBurst = isBurst;
            this.burstMagnitude = burstMagnitude;
            this.burstScore = burstScore;
            this.baselineMean = baselineMean;
            this.baselineStd = baselineStd;
            this.adjustmentFactor = calculateAdjustmentFactor();
        }

        private double calculateAdjustmentFactor() {
            if (!isBurst || baselineMean <= 0) {
                return 1.0;
            }
            double ratio = burstMagnitude / baselineMean;
            if (ratio <= 1.5) {
                return 1.0;
            } else if (ratio <= 2.0) {
                return 1.2;
            } else if (ratio <= 3.0) {
                return 1.5;
            } else if (ratio <= 5.0) {
                return 2.0;
            } else {
                return Math.min(3.0, 1.0 + Math.log(ratio) / Math.log(2));
            }
        }

        public boolean isBurst() { return isBurst; }
        public double getBurstMagnitude() { return burstMagnitude; }
        public double getBurstScore() { return burstScore; }
        public double getBaselineMean() { return baselineMean; }
        public double getBaselineStd() { return baselineStd; }
        public double getAdjustmentFactor() { return adjustmentFactor; }
    }

    public static BurstDetectionResult detectBurst(List<Double> values, int burstWindowSize,
                                                   double zScoreThreshold) {
        if (values == null || values.size() < burstWindowSize + 5) {
            return new BurstDetectionResult(false, 0, 0, 0, 0);
        }

        int totalSize = values.size();
        int baselineSize = totalSize - burstWindowSize;

        List<Double> baselineValues = values.subList(0, baselineSize);
        List<Double> burstWindowValues = values.subList(baselineSize, totalSize);

        double baselineMean = mean(baselineValues);
        double baselineStd = standardDeviation(baselineValues);
        double burstMean = mean(burstWindowValues);

        if (baselineMean <= 0 || baselineStd <= 0) {
            return new BurstDetectionResult(false, burstMean, 0, baselineMean, baselineStd);
        }

        double zScore = (burstMean - baselineMean) / baselineStd;
        double magnitude = burstMean - baselineMean;

        boolean isBurst = zScore > zScoreThreshold && magnitude > baselineMean * 0.3;

        return new BurstDetectionResult(isBurst, magnitude, zScore, baselineMean, baselineStd);
    }

    public static BurstDetectionResult detectBurst(List<Double> values) {
        return detectBurst(values, Math.min(5, values.size() / 4), 2.0);
    }

    public static double calculateBurstAdjustedForecast(double originalForecast,
                                                        BurstDetectionResult burstResult) {
        if (burstResult == null || !burstResult.isBurst()) {
            return originalForecast;
        }
        return originalForecast * burstResult.getAdjustmentFactor();
    }

    public static double[] detectChangepoint(List<Double> values) {
        if (values == null || values.size() < 10) {
            return new double[]{0, 0};
        }

        double bestScore = Double.NEGATIVE_INFINITY;
        int bestIndex = -1;

        for (int i = 5; i < values.size() - 5; i++) {
            List<Double> pre = values.subList(0, i);
            List<Double> post = values.subList(i, values.size());

            double preMean = mean(pre);
            double postMean = mean(post);
            double preStd = standardDeviation(pre);
            double postStd = standardDeviation(post);

            if (preStd == 0 || postStd == 0) continue;

            double score = Math.abs(postMean - preMean) / Math.sqrt((preStd * preStd + postStd * postStd) / 2);
            if (score > bestScore) {
                bestScore = score;
                bestIndex = i;
            }
        }

        return new double[]{bestIndex, bestScore};
    }
}

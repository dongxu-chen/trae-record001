package com.oauth2.monitor.anomaly;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.DoubleAdder;
import java.util.concurrent.atomic.DoubleAccumulator;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricsBaseline {

    private String metricName;
    private Instant windowStart;
    private Instant windowEnd;
    private Duration windowSize;

    private long sampleCount;
    private double mean;
    private double standardDeviation;
    private double variance;
    private double min;
    private double max;
    private double p50;
    private double p95;
    private double p99;
    private double sum;

    private double upperBound3Sigma;
    private double lowerBound3Sigma;
    private double upperBound2Sigma;
    private double lowerBound2Sigma;

    private boolean initialized;
    private Instant lastUpdated;

    public enum AnomalyLevel {
        NORMAL,
        WARNING,
        CRITICAL,
        EXTREME
    }

    public AnomalyLevel checkAnomaly(double value) {
        if (!initialized || sampleCount < 30) {
            return AnomalyLevel.NORMAL;
        }

        double zScore = calculateZScore(value);

        if (Math.abs(zScore) >= 4.0) {
            return AnomalyLevel.EXTREME;
        } else if (Math.abs(zScore) >= 3.0) {
            return AnomalyLevel.CRITICAL;
        } else if (Math.abs(zScore) >= 2.0) {
            return AnomalyLevel.WARNING;
        }

        return AnomalyLevel.NORMAL;
    }

    public double calculateZScore(double value) {
        if (standardDeviation == 0) {
            return 0;
        }
        return (value - mean) / standardDeviation;
    }

    public double getDeviationPercentage(double value) {
        if (mean == 0) {
            return 0;
        }
        return ((value - mean) / Math.abs(mean)) * 100;
    }

    public boolean isSpike(double value) {
        return value > upperBound3Sigma;
    }

    public boolean isDrop(double value) {
        return value < lowerBound3Sigma;
    }

    public boolean isAbnormal(double value) {
        return value > upperBound2Sigma || value < lowerBound2Sigma;
    }

    public String getAnomalyDescription(double value) {
        AnomalyLevel level = checkAnomaly(value);
        if (level == AnomalyLevel.NORMAL) {
            return String.format("Value %.2f is within normal range (mean=%.2f, σ=%.2f)",
                    value, mean, standardDeviation);
        }

        double zScore = calculateZScore(value);
        double deviation = getDeviationPercentage(value);
        String direction = value > mean ? "above" : "below";

        return String.format(
                "%s anomaly: value %.2f is %.2fσ %s mean (deviation: %.1f%%). " +
                        "Normal range: [%.2f, %.2f] (2σ) or [%.2f, %.2f] (3σ)",
                level, value, Math.abs(zScore), direction, deviation,
                lowerBound2Sigma, upperBound2Sigma,
                lowerBound3Sigma, upperBound3Sigma
        );
    }

    public static MetricsBaseline fromSamples(double[] samples) {
        if (samples == null || samples.length == 0) {
            return MetricsBaseline.builder()
                    .initialized(false)
                    .sampleCount(0)
                    .build();
        }

        int n = samples.length;
        double sum = 0;
        double min = Double.MAX_VALUE;
        double max = Double.MIN_VALUE;

        for (double sample : samples) {
            sum += sample;
            min = Math.min(min, sample);
            max = Math.max(max, sample);
        }

        double mean = sum / n;

        double varianceSum = 0;
        for (double sample : samples) {
            varianceSum += Math.pow(sample - mean, 2);
        }
        double variance = varianceSum / (n - 1);
        double stdDev = Math.sqrt(variance);

        Arrays.sort(samples);
        double p50 = samples[n / 2];
        double p95 = samples[(int) (n * 0.95)];
        double p99 = samples[(int) (n * 0.99)];

        return MetricsBaseline.builder()
                .sampleCount(n)
                .mean(mean)
                .standardDeviation(stdDev)
                .variance(variance)
                .min(min)
                .max(max)
                .p50(p50)
                .p95(p95)
                .p99(p99)
                .sum(sum)
                .upperBound3Sigma(mean + 3 * stdDev)
                .lowerBound3Sigma(Math.max(0, mean - 3 * stdDev))
                .upperBound2Sigma(mean + 2 * stdDev)
                .lowerBound2Sigma(Math.max(0, mean - 2 * stdDev))
                .initialized(true)
                .lastUpdated(Instant.now())
                .build();
    }

    public static class RollingStats {
        private final int windowSize;
        private final DoubleAdder sum = new DoubleAdder();
        private final DoubleAdder sumOfSquares = new DoubleAdder();
        private final AtomicLong count = new AtomicLong(0);
        private final DoubleAccumulator min = new DoubleAccumulator(Double::min, Double.MAX_VALUE);
        private final DoubleAccumulator max = new DoubleAccumulator(Double::max, Double.MIN_VALUE);

        public RollingStats(int windowSize) {
            this.windowSize = windowSize;
        }

        public void add(double value) {
            sum.add(value);
            sumOfSquares.add(value * value);
            count.incrementAndGet();
            min.accumulate(value);
            max.accumulate(value);
        }

        public double getMean() {
            long n = count.get();
            return n > 0 ? sum.sum() / n : 0;
        }

        public double getStandardDeviation() {
            long n = count.get();
            if (n < 2) return 0;
            double mean = getMean();
            double variance = (sumOfSquares.sum() / n) - (mean * mean);
            return Math.sqrt(Math.max(0, variance));
        }

        public long getCount() {
            return count.get();
        }

        public double getMin() {
            return min.get();
        }

        public double getMax() {
            return max.get();
        }

        public void reset() {
            sum.reset();
            sumOfSquares.reset();
            count.set(0);
            min.reset();
            max.reset();
        }
    }
}

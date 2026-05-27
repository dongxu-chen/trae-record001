package com.datasecurity.masking.dp;

import lombok.extern.slf4j.Slf4j;

import java.security.SecureRandom;
import java.util.Random;

@Slf4j
public class DifferentialPrivacy {

    private static final Random RANDOM = new SecureRandom();

    private DifferentialPrivacy() {
    }

    public static double addLaplaceNoise(double value, double epsilon, double sensitivity) {
        double scale = sensitivity / epsilon;
        double noise = sampleLaplace(0, scale);
        log.debug("Adding Laplace noise: value={}, epsilon={}, sensitivity={}, noise={}",
                value, epsilon, sensitivity, noise);
        return value + noise;
    }

    public static long addLaplaceNoise(long value, double epsilon, double sensitivity) {
        return Math.round(addLaplaceNoise((double) value, epsilon, sensitivity));
    }

    public static int addLaplaceNoise(int value, double epsilon, double sensitivity) {
        return (int) Math.round(addLaplaceNoise((double) value, epsilon, sensitivity));
    }

    public static double sampleLaplace(double location, double scale) {
        double u = RANDOM.nextDouble() - 0.5;
        return location - scale * Math.signum(u) * Math.log(1 - 2 * Math.abs(u));
    }

    public static double addGaussianNoise(double value, double epsilon, double delta, double sensitivity) {
        double sigma = sensitivity * Math.sqrt(2 * Math.log(1.25 / delta)) / epsilon;
        double noise = RANDOM.nextGaussian() * sigma;
        log.debug("Adding Gaussian noise: value={}, epsilon={}, delta={}, sensitivity={}, noise={}",
                value, epsilon, delta, sensitivity, noise);
        return value + noise;
    }

    public static long addGaussianNoise(long value, double epsilon, double delta, double sensitivity) {
        return Math.round(addGaussianNoise((double) value, epsilon, delta, sensitivity));
    }

    public static int exponentialMechanism(double[] scores, double epsilon, double sensitivity) {
        double[] weights = new double[scores.length];
        double maxScore = Double.NEGATIVE_INFINITY;

        for (double score : scores) {
            if (score > maxScore) {
                maxScore = score;
            }
        }

        double sum = 0;
        for (int i = 0; i < scores.length; i++) {
            weights[i] = Math.exp((epsilon * (scores[i] - maxScore)) / (2 * sensitivity));
            sum += weights[i];
        }

        double r = RANDOM.nextDouble() * sum;
        double cumulative = 0;
        for (int i = 0; i < weights.length; i++) {
            cumulative += weights[i];
            if (r <= cumulative) {
                log.debug("Exponential mechanism selected index: {}, score: {}", i, scores[i]);
                return i;
            }
        }

        return scores.length - 1;
    }

    public static double[] privatizeHistogram(int[] counts, double epsilon) {
        double sensitivity = 2.0;
        double[] noisyCounts = new double[counts.length];

        for (int i = 0; i < counts.length; i++) {
            noisyCounts[i] = addLaplaceNoise(counts[i], epsilon, sensitivity);
            if (noisyCounts[i] < 0) {
                noisyCounts[i] = 0;
            }
        }

        return noisyCounts;
    }

    public static double computeAverage(double[] values, double epsilon, double min, double max) {
        double sensitivity = (max - min) / values.length;
        double sum = 0;

        for (double value : values) {
            double clamped = Math.max(min, Math.min(max, value));
            sum += clamped;
        }

        double average = sum / values.length;
        return addLaplaceNoise(average, epsilon, sensitivity);
    }

    public static double computeSum(double[] values, double epsilon, double min, double max) {
        double sensitivity = max - min;
        double sum = 0;

        for (double value : values) {
            double clamped = Math.max(min, Math.min(max, value));
            sum += clamped;
        }

        return addLaplaceNoise(sum, epsilon, sensitivity);
    }

    public static double computeVariance(double[] values, double epsilon, double min, double max) {
        double mean = computeAverage(values, epsilon / 2, min, max);
        double sumSquaredDeviations = 0;

        for (double value : values) {
            double clamped = Math.max(min, Math.min(max, value));
            sumSquaredDeviations += Math.pow(clamped - mean, 2);
        }

        double variance = sumSquaredDeviations / values.length;
        double sensitivity = Math.pow(max - min, 2) / values.length;

        return addLaplaceNoise(variance, epsilon / 2, sensitivity);
    }

    public static boolean satisfyEpsilonDelta(double epsilonUsed, double deltaUsed,
                                           double epsilonBudget, double deltaBudget) {
        return epsilonUsed <= epsilonBudget && deltaUsed <= deltaBudget;
    }

    public static double computeAdvancedComposition(double epsilon, double delta, int k, double deltaPrime) {
        return k * epsilon * Math.sqrt(2 * k * Math.log(1 / deltaPrime)) + k * epsilon * (Math.exp(epsilon) - 1);
    }
}

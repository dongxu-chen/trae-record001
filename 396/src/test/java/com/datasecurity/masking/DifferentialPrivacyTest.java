package com.datasecurity.masking;

import com.datasecurity.masking.dp.DifferentialPrivacy;
import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.*;

class DifferentialPrivacyTest {

    private static final int NUM_SAMPLES = 10000;
    private static final double TOLERANCE = 0.1;

    @Test
    void testAddLaplaceNoiseDouble() {
        double value = 100.0;
        double epsilon = 1.0;
        double sensitivity = 1.0;

        int countNearTrueValue = 0;
        for (int i = 0; i < NUM_SAMPLES; i++) {
            double noisy = DifferentialPrivacy.addLaplaceNoise(value, epsilon, sensitivity);
            if (Math.abs(noisy - value) < 5.0) {
                countNearTrueValue++;
            }
        }

        assertTrue(countNearTrueValue > NUM_SAMPLES * 0.6,
                "More than 60% of noisy values should be within 5 of true value");
    }

    @Test
    void testAddLaplaceNoiseLong() {
        long value = 1000L;
        double epsilon = 1.0;
        double sensitivity = 1.0;

        long noisy = DifferentialPrivacy.addLaplaceNoise(value, epsilon, sensitivity);

        assertNotEquals(value, noisy);
        assertTrue(noisy >= value - 10 && noisy <= value + 10,
                "Noisy value should be reasonably close to true value");
    }

    @Test
    void testAddLaplaceNoiseInt() {
        int value = 500;
        double epsilon = 1.0;
        double sensitivity = 1.0;

        int noisy = DifferentialPrivacy.addLaplaceNoise(value, epsilon, sensitivity);

        assertNotEquals(value, noisy);
    }

    @Test
    void testSampleLaplace() {
        double mean = 0;
        double scale = 1.0;

        double sum = 0;
        for (int i = 0; i < NUM_SAMPLES; i++) {
            sum += DifferentialPrivacy.sampleLaplace(mean, scale);
        }
        double sampleMean = sum / NUM_SAMPLES;

        assertTrue(Math.abs(sampleMean) < TOLERANCE,
                "Sample mean should be close to 0, got: " + sampleMean);
    }

    @Test
    void testAddGaussianNoise() {
        double value = 100.0;
        double epsilon = 1.0;
        double delta = 1e-5;
        double sensitivity = 1.0;

        int countNearTrueValue = 0;
        for (int i = 0; i < NUM_SAMPLES; i++) {
            double noisy = DifferentialPrivacy.addGaussianNoise(value, epsilon, delta, sensitivity);
            if (Math.abs(noisy - value) < 3.0) {
                countNearTrueValue++;
            }
        }

        assertTrue(countNearTrueValue > NUM_SAMPLES * 0.68,
                "About 68% of values should be within 1 standard deviation");
    }

    @Test
    void testExponentialMechanism() {
        double[] scores = {10.0, 8.0, 5.0, 3.0, 1.0};
        double epsilon = 1.0;
        double sensitivity = 1.0;

        int[] counts = new int[scores.length];
        for (int i = 0; i < NUM_SAMPLES; i++) {
            int selected = DifferentialPrivacy.exponentialMechanism(scores, epsilon, sensitivity);
            counts[selected]++;
        }

        assertTrue(counts[0] > counts[1],
                "Highest score should be selected most often");
        assertTrue(counts[1] > counts[2],
                "Second highest score should be selected second most often");

        System.out.println("Exponential mechanism distribution:");
        for (int i = 0; i < counts.length; i++) {
            System.out.printf("  Score %.1f: %d times (%.1f%%)%n",
                    scores[i], counts[i], 100.0 * counts[i] / NUM_SAMPLES);
        }
    }

    @Test
    void testPrivatizeHistogram() {
        int[] counts = {100, 200, 150, 300, 250};
        double epsilon = 1.0;

        double[] noisyCounts = DifferentialPrivacy.privatizeHistogram(counts, epsilon);

        assertEquals(counts.length, noisyCounts.length);

        for (int i = 0; i < counts.length; i++) {
            assertTrue(noisyCounts[i] >= 0, "Noisy counts should be non-negative");
            assertNotEquals(counts[i], noisyCounts[i], 0.001,
                    "Count should be noisy");
        }

        double trueSum = Arrays.stream(counts).sum();
        double noisySum = Arrays.stream(noisyCounts).sum();
        assertTrue(Math.abs(noisySum - trueSum) / trueSum < 0.1,
                "Sum should be within 10% of true sum");
    }

    @Test
    void testComputeAverage() {
        double[] values = {10.0, 20.0, 30.0, 40.0, 50.0};
        double epsilon = 1.0;
        double min = 0.0;
        double max = 100.0;

        double trueAverage = 30.0;
        double noisyAverage = DifferentialPrivacy.computeAverage(values, epsilon, min, max);

        assertNotEquals(trueAverage, noisyAverage, 0.001);
        assertTrue(Math.abs(noisyAverage - trueAverage) < 10.0,
                "Noisy average should be reasonably close to true average");
    }

    @Test
    void testComputeSum() {
        double[] values = {10.0, 20.0, 30.0, 40.0, 50.0};
        double epsilon = 1.0;
        double min = 0.0;
        double max = 100.0;

        double trueSum = 150.0;
        double noisySum = DifferentialPrivacy.computeSum(values, epsilon, min, max);

        assertNotEquals(trueSum, noisySum, 0.001);
        assertTrue(Math.abs(noisySum - trueSum) < 50.0,
                "Noisy sum should be reasonably close to true sum");
    }

    @Test
    void testComputeVariance() {
        double[] values = {10.0, 20.0, 30.0, 40.0, 50.0};
        double epsilon = 1.0;
        double min = 0.0;
        double max = 100.0;

        double trueVariance = 200.0;
        double noisyVariance = DifferentialPrivacy.computeVariance(values, epsilon, min, max);

        assertNotEquals(trueVariance, noisyVariance, 0.001);
        assertTrue(noisyVariance >= 0, "Variance should be non-negative");
    }

    @Test
    void testSatisfyEpsilonDelta() {
        assertTrue(DifferentialPrivacy.satisfyEpsilonDelta(0.5, 1e-6, 1.0, 1e-5));
        assertTrue(DifferentialPrivacy.satisfyEpsilonDelta(1.0, 1e-5, 1.0, 1e-5));
        assertFalse(DifferentialPrivacy.satisfyEpsilonDelta(1.5, 1e-5, 1.0, 1e-5));
        assertFalse(DifferentialPrivacy.satisfyEpsilonDelta(0.5, 1e-4, 1.0, 1e-5));
    }

    @Test
    void testEpsilonEffect() {
        double value = 100.0;
        double sensitivity = 1.0;

        double sumSmallEpsilon = 0;
        double sumLargeEpsilon = 0;

        for (int i = 0; i < NUM_SAMPLES; i++) {
            sumSmallEpsilon += Math.abs(DifferentialPrivacy.addLaplaceNoise(value, 0.1, sensitivity) - value);
            sumLargeEpsilon += Math.abs(DifferentialPrivacy.addLaplaceNoise(value, 10.0, sensitivity) - value);
        }

        double avgNoiseSmallEpsilon = sumSmallEpsilon / NUM_SAMPLES;
        double avgNoiseLargeEpsilon = sumLargeEpsilon / NUM_SAMPLES;

        assertTrue(avgNoiseSmallEpsilon > avgNoiseLargeEpsilon,
                "Smaller epsilon should produce larger noise");

        System.out.printf("Average noise with epsilon=0.1: %.4f%n", avgNoiseSmallEpsilon);
        System.out.printf("Average noise with epsilon=10.0: %.4f%n", avgNoiseLargeEpsilon);
    }

    @Test
    void testSensitivityEffect() {
        double value = 100.0;
        double epsilon = 1.0;

        double sumLowSensitivity = 0;
        double sumHighSensitivity = 0;

        for (int i = 0; i < NUM_SAMPLES; i++) {
            sumLowSensitivity += Math.abs(DifferentialPrivacy.addLaplaceNoise(value, epsilon, 1.0) - value);
            sumHighSensitivity += Math.abs(DifferentialPrivacy.addLaplaceNoise(value, epsilon, 10.0) - value);
        }

        double avgNoiseLowSensitivity = sumLowSensitivity / NUM_SAMPLES;
        double avgNoiseHighSensitivity = sumHighSensitivity / NUM_SAMPLES;

        assertTrue(avgNoiseHighSensitivity > avgNoiseLowSensitivity,
                "Higher sensitivity should produce larger noise");
    }
}

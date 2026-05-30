package com.distid.metrics;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.util.Random;

import static org.junit.jupiter.api.Assertions.*;

class TDigestPercentilesTest {

    @Test
    void shouldCalculatePercentilesAccurately() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        TDigestPercentiles percentiles = new TDigestPercentiles(registry, "test");

        for (int i = 1; i <= 100; i++) {
            percentiles.record(i);
        }

        double p50 = percentiles.getPercentile(0.50);
        double p90 = percentiles.getPercentile(0.90);
        double p99 = percentiles.getPercentile(0.99);

        assertTrue(p50 >= 45 && p50 <= 55, "P50 should be around 50, got: " + p50);
        assertTrue(p90 >= 85 && p90 <= 95, "P90 should be around 90, got: " + p90);
        assertTrue(p99 >= 94 && p99 <= 100, "P99 should be around 99, got: " + p99);
    }

    @Test
    void shouldHandleLargeDataSet() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        TDigestPercentiles percentiles = new TDigestPercentiles(registry, "test");

        Random random = new Random(42);
        for (int i = 0; i < 10000; i++) {
            percentiles.record(random.nextGaussian() * 100 + 500);
        }

        double p50 = percentiles.getPercentile(0.50);
        double p99 = percentiles.getPercentile(0.99);

        assertTrue(p50 >= 480 && p50 <= 520, "P50 should be around mean");
        assertTrue(p99 > p50, "P99 should be greater than P50");
    }

    @Test
    void shouldReturnZeroForEmptyDigest() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        TDigestPercentiles percentiles = new TDigestPercentiles(registry, "test");

        assertEquals(0.0, percentiles.getPercentile(0.50), 0.01);
    }

    @Test
    void shouldTrackCount() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        TDigestPercentiles percentiles = new TDigestPercentiles(registry, "test");

        assertEquals(0, percentiles.getCount());

        for (int i = 0; i < 100; i++) {
            percentiles.record(i);
        }

        assertTrue(percentiles.getCount() >= 100);
    }
}

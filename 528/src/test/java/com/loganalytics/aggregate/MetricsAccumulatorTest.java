package com.loganalytics.aggregate;

import org.junit.Test;
import static org.junit.Assert.*;

public class MetricsAccumulatorTest {

    @Test
    public void testTDigestPercentiles() {
        MetricsAccumulator accumulator = new MetricsAccumulator(100.0);

        for (int i = 1; i <= 1000; i++) {
            accumulator.add(i, false);
        }

        assertEquals(1000, accumulator.getTotalRequests());
        assertEquals(0, accumulator.getErrorRequests());
        assertEquals(500.5, accumulator.getMean(), 5.0);
        assertEquals(500.0, accumulator.getP50(), 50.0);
        assertEquals(950.0, accumulator.getP95(), 50.0);
        assertEquals(990.0, accumulator.getP99(), 50.0);
        assertTrue(accumulator.getP999() > 995.0);
    }

    @Test
    public void testErrorRate() {
        MetricsAccumulator accumulator = new MetricsAccumulator(100.0);

        for (int i = 0; i < 100; i++) {
            accumulator.add(100.0, i < 10);
        }

        assertEquals(100, accumulator.getTotalRequests());
        assertEquals(10, accumulator.getErrorRequests());
        assertEquals(10.0, accumulator.getErrorRate(), 0.01);
    }

    @Test
    public void testStatsCalculation() {
        MetricsAccumulator accumulator = new MetricsAccumulator(100.0);

        accumulator.add(100.0, false);
        accumulator.add(200.0, false);
        accumulator.add(300.0, false);

        assertEquals(200.0, accumulator.getMean(), 0.01);
        assertEquals(100.0, accumulator.getMinLatency(), 0.01);
        assertEquals(300.0, accumulator.getMaxLatency(), 0.01);
        assertEquals(100.0, accumulator.getStdDev(), 5.0);
    }

    @Test
    public void testMerge() {
        MetricsAccumulator a1 = new MetricsAccumulator(100.0);
        MetricsAccumulator a2 = new MetricsAccumulator(100.0);

        for (int i = 0; i < 100; i++) {
            a1.add(i, i < 10);
            a2.add(100 + i, i < 20);
        }

        a1.merge(a2);

        assertEquals(200, a1.getTotalRequests());
        assertEquals(30, a1.getErrorRequests());
        assertEquals(15.0, a1.getErrorRate(), 0.01);
        assertTrue(a1.getP50() > 50 && a1.getP50() < 150);
    }
}

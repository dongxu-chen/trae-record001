package com.log.collector.util;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class LatencyMonitorTest {

    private LatencyMonitor monitor;

    @Before
    public void setUp() {
        monitor = LatencyMonitor.getInstance();
        monitor.reset();
    }

    @Test
    public void testSingleton() {
        LatencyMonitor another = LatencyMonitor.getInstance();
        assertSame(monitor, another);
    }

    @Test
    public void testRecordLatency() {
        long now = System.currentTimeMillis();
        monitor.recordLatency(now - 100, now, "INFO");
        monitor.recordLatency(now - 200, now, "ERROR");
        monitor.recordLatency(now - 50, now, "DEBUG");

        assertEquals(3, monitor.getTotalEvents());
        assertTrue(monitor.getAverageLatency() > 0);
        assertTrue(monitor.getMinLatency() <= monitor.getMaxLatency());
    }

    @Test
    public void testBucketDistribution() {
        long now = System.currentTimeMillis();

        for (int i = 0; i < 100; i++) {
            monitor.recordLatency(now - 5, now, "INFO");
        }
        for (int i = 0; i < 50; i++) {
            monitor.recordLatency(now - 100, now, "ERROR");
        }

        assertEquals(150, monitor.getTotalEvents());
        assertTrue(monitor.getAverageLatency() > 0);
    }

    @Test
    public void testNegativeLatency() {
        long now = System.currentTimeMillis();
        monitor.recordLatency(now + 100, now, "INFO");

        assertEquals(1, monitor.getTotalEvents());
        assertEquals(0, monitor.getMinLatency());
    }

    @Test
    public void testReset() {
        long now = System.currentTimeMillis();
        monitor.recordLatency(now - 100, now, "INFO");

        assertEquals(1, monitor.getTotalEvents());

        monitor.reset();

        assertEquals(0, monitor.getTotalEvents());
        assertEquals(0.0, monitor.getAverageLatency(), 0.001);
    }

    @Test
    public void testEventLatencyClass() {
        LatencyMonitor.EventLatency event = new LatencyMonitor.EventLatency(
            System.currentTimeMillis() - 100,
            System.currentTimeMillis(),
            "INFO",
            "test-service"
        );

        assertEquals("INFO", event.level);
        assertEquals("test-service", event.service);
    }

    @Test
    public void testReportStats() {
        long now = System.currentTimeMillis();
        for (int i = 0; i < 10; i++) {
            monitor.recordLatency(now - i * 10, now, "INFO");
        }

        monitor.reportStats();
    }
}

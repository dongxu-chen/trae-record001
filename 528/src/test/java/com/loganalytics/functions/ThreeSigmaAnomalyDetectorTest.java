package com.loganalytics.functions;

import com.loganalytics.model.AlertEvent;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.util.Collector;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class ThreeSigmaAnomalyDetectorTest {

    @Test
    public void testErrorRateAnomalyDetection() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(50.0)
                .errorRateMean(5.0)
                .errorRateStdDev(3.0)
                .build();

        detector.flatMap(metrics, collector);

        assertFalse(alerts.isEmpty());
        AlertEvent alert = alerts.get(0);
        assertEquals("ERROR_RATE_ANOMALY", alert.getAlertType());
        assertEquals(50.0, alert.getCurrentValue(), 0.01);
        assertEquals(14.0, alert.getThreshold(), 0.01);
    }

    @Test
    public void testLatencyAnomalyDetection() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .p99Latency(5000.0)
                .latencyMean(100.0)
                .latencyStdDev(50.0)
                .build();

        detector.flatMap(metrics, collector);

        assertFalse(alerts.isEmpty());
        AlertEvent alert = alerts.get(0);
        assertEquals("LATENCY_ANOMALY", alert.getAlertType());
        assertEquals(5000.0, alert.getCurrentValue(), 0.01);
        assertEquals(250.0, alert.getThreshold(), 0.01);
    }

    @Test
    public void testQpsSpikeDetection() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("all")
                .value("total")
                .qps(50000.0)
                .qpsMean(1000.0)
                .qpsStdDev(500.0)
                .build();

        detector.flatMap(metrics, collector);

        assertFalse(alerts.isEmpty());
        AlertEvent alert = alerts.get(0);
        assertEquals("QPS_SPIKE", alert.getAlertType());
        assertEquals(50000.0, alert.getCurrentValue(), 0.01);
        assertEquals(2500.0, alert.getThreshold(), 0.01);
    }

    @Test
    public void testQpsDropDetection() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("all")
                .value("total")
                .qps(100.0)
                .qpsMean(1000.0)
                .qpsStdDev(200.0)
                .build();

        detector.flatMap(metrics, collector);

        assertFalse(alerts.isEmpty());
        AlertEvent alert = alerts.get(0);
        assertEquals("QPS_DROP", alert.getAlertType());
        assertEquals(100.0, alert.getCurrentValue(), 0.01);
        assertEquals(400.0, alert.getThreshold(), 0.01);
    }

    @Test
    public void testNoAnomalyWhenWithinBounds() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(3.0)
                .errorRateMean(5.0)
                .errorRateStdDev(2.0)
                .p99Latency(150.0)
                .latencyMean(100.0)
                .latencyStdDev(50.0)
                .qps(1500.0)
                .qpsMean(1000.0)
                .qpsStdDev(500.0)
                .build();

        detector.flatMap(metrics, collector);

        assertTrue(alerts.isEmpty());
    }

    @Test
    public void testStaticFallbackWhenNoHistory() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(10.0)
                .errorRateMean(0.0)
                .errorRateStdDev(0.0)
                .p99Latency(2000.0)
                .latencyMean(0.0)
                .latencyStdDev(0.0)
                .qps(20000.0)
                .qpsMean(0.0)
                .qpsStdDev(0.0)
                .build();

        detector.flatMap(metrics, collector);

        assertEquals(3, alerts.size());
        assertTrue(alerts.stream().anyMatch(a -> a.getAlertType().equals("ERROR_RATE_STATIC")));
        assertTrue(alerts.stream().anyMatch(a -> a.getAlertType().equals("LATENCY_STATIC")));
        assertTrue(alerts.stream().anyMatch(a -> a.getAlertType().equals("QPS_STATIC")));
    }

    @Test
    public void testSeverityLevels() {
        List<AlertEvent> alerts = new ArrayList<>();
        Collector<AlertEvent> collector = new ListCollector<>(alerts);

        ThreeSigmaAnomalyDetector detector = new ThreeSigmaAnomalyDetector(3.0, 10);

        MetricsResult infoMetrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(20.0)
                .errorRateMean(5.0)
                .errorRateStdDev(3.0)
                .build();
        detector.flatMap(infoMetrics, collector);
        assertEquals("INFO", alerts.get(0).getSeverity());

        alerts.clear();
        MetricsResult warningMetrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(35.0)
                .errorRateMean(5.0)
                .errorRateStdDev(3.0)
                .build();
        detector.flatMap(warningMetrics, collector);
        assertEquals("WARNING", alerts.get(0).getSeverity());

        alerts.clear();
        MetricsResult criticalMetrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/test")
                .errorRate(100.0)
                .errorRateMean(5.0)
                .errorRateStdDev(3.0)
                .build();
        detector.flatMap(criticalMetrics, collector);
        assertEquals("CRITICAL", alerts.get(0).getSeverity());
    }

    private static class ListCollector<T> implements Collector<T> {
        private final List<T> list;

        public ListCollector(List<T> list) {
            this.list = list;
        }

        @Override
        public void collect(T record) {
            list.add(record);
        }

        @Override
        public void close() {
        }
    }
}

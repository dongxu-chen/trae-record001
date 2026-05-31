package com.oauth2.monitor;

import com.oauth2.monitor.anomaly.BaselineLearningService;
import com.oauth2.monitor.anomaly.MetricsBaseline;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Baseline Learning Service Tests")
class BaselineLearningServiceTest {

    private BaselineLearningService baselineService;
    private SimpleMeterRegistry meterRegistry;

    @BeforeEach
    void setUp() {
        meterRegistry = new SimpleMeterRegistry();
        baselineService = new BaselineLearningService(meterRegistry);
    }

    @Test
    @DisplayName("Test default metrics are registered")
    void testDefaultMetricsRegistered() {
        List<String> metrics = baselineService.getMonitoredMetrics();
        assertFalse(metrics.isEmpty(), "Default metrics should be registered");
        assertTrue(metrics.contains("token_request_rate"));
        assertTrue(metrics.contains("token_failure_rate"));
    }

    @Test
    @DisplayName("Test custom metric registration")
    void testCustomMetricRegistration() {
        baselineService.registerMetric("custom_test_metric");
        List<String> metrics = baselineService.getMonitoredMetrics();
        assertTrue(metrics.contains("custom_test_metric"));
    }

    @Test
    @DisplayName("Test sample recording and baseline building")
    void testSampleRecordingAndBaselineBuilding() {
        for (int i = 0; i < 50; i++) {
            baselineService.recordSample("token_request_rate", 100 + Math.random() * 10);
        }

        baselineService.updateBaselines();

        MetricsBaseline baseline = baselineService.getBaseline("token_request_rate");
        assertTrue(baseline.isInitialized(), "Baseline should be initialized after enough samples");
        assertTrue(baseline.getMean() > 99 && baseline.getMean() < 115,
                "Mean should be around 100-110");
        assertTrue(baseline.getStandardDeviation() >= 0, "StdDev should be non-negative");
        assertTrue(baseline.getSampleCount() >= 30);
    }

    @Test
    @DisplayName("Test baseline not built with insufficient samples")
    void testBaselineNotBuiltWithInsufficientSamples() {
        for (int i = 0; i < 10; i++) {
            baselineService.recordSample("token_request_rate", 100.0);
        }

        baselineService.updateBaselines();

        MetricsBaseline baseline = baselineService.getBaseline("token_request_rate");
        assertFalse(baseline.isInitialized(), "Baseline should not be initialized with < 30 samples");
    }

    @Test
    @DisplayName("Test anomaly detection - normal value")
    void testAnomalyDetectionNormalValue() {
        for (int i = 0; i < 50; i++) {
            baselineService.recordSample("token_failure_rate", 5.0 + Math.random() * 2);
        }
        baselineService.updateBaselines();

        MetricsBaseline.AnomalyLevel level = baselineService.checkAnomaly("token_failure_rate", 6.0);
        assertEquals(MetricsBaseline.AnomalyLevel.NORMAL, level,
                "Value near mean should be NORMAL");
    }

    @Test
    @DisplayName("Test anomaly detection - extreme value")
    void testAnomalyDetectionExtremeValue() {
        for (int i = 0; i < 100; i++) {
            baselineService.recordSample("token_failure_rate", 5.0);
        }
        baselineService.updateBaselines();

        MetricsBaseline.AnomalyLevel level = baselineService.checkAnomaly("token_failure_rate", 100.0);
        assertEquals(MetricsBaseline.AnomalyLevel.EXTREME, level,
                "Very high value should be EXTREME");
    }

    @Test
    @DisplayName("Test Z-score calculation")
    void testZScoreCalculation() {
        for (int i = 0; i < 100; i++) {
            baselineService.recordSample("test_metric", 50.0);
        }
        baselineService.updateBaselines();

        MetricsBaseline baseline = baselineService.getBaseline("test_metric");
        assertEquals(0.0, baseline.calculateZScore(50.0), 0.01,
                "Z-score of mean should be 0");
    }

    @Test
    @DisplayName("Test scan for anomalies")
    void testScanForAnomalies() {
        for (int i = 0; i < 100; i++) {
            baselineService.recordSample("token_failure_rate", 5.0);
            baselineService.recordSample("authorization_code_failure_rate", 3.0);
        }
        baselineService.updateBaselines();

        Map<String, Double> currentValues = new HashMap<>();
        currentValues.put("token_failure_rate", 50.0);
        currentValues.put("authorization_code_failure_rate", 3.5);

        List<BaselineLearningService.AnomalyResult> anomalies =
                baselineService.scanForAnomalies(currentValues);

        assertFalse(anomalies.isEmpty(), "Should detect anomaly for token_failure_rate=50");
        assertTrue(anomalies.stream()
                .anyMatch(a -> a.getMetricName().equals("token_failure_rate")));
    }

    @Test
    @DisplayName("Test analyze anomaly with details")
    void testAnalyzeAnomalyWithDetails() {
        for (int i = 0; i < 100; i++) {
            baselineService.recordSample("test_metric", 10.0);
        }
        baselineService.updateBaselines();

        BaselineLearningService.AnomalyResult result =
                baselineService.analyzeAnomaly("test_metric", 100.0);

        assertEquals("test_metric", result.getMetricName());
        assertEquals(100.0, result.getValue());
        assertTrue(result.getZScore() > 2, "Z-score should be high for extreme value");
        assertNotNull(result.getDescription());
        assertNotNull(result.getTimestamp());
    }

    @Test
    @DisplayName("Test baseline recalculation")
    void testBaselineRecalculation() {
        for (int i = 0; i < 50; i++) {
            baselineService.recordSample("recalc_metric", 20.0);
        }

        baselineService.triggerBaselineRecalculation("recalc_metric");

        MetricsBaseline baseline = baselineService.getBaseline("recalc_metric");
        assertTrue(baseline.isInitialized());
        assertEquals(20.0, baseline.getMean(), 0.01);
    }

    @Test
    @DisplayName("Test all baselines retrieval")
    void testGetAllBaselines() {
        for (int i = 0; i < 50; i++) {
            baselineService.recordSample("token_request_rate", 100.0);
            baselineService.recordSample("token_failure_rate", 5.0);
        }
        baselineService.updateBaselines();

        Map<String, MetricsBaseline> allBaselines = baselineService.getAllBaselines();
        assertFalse(allBaselines.isEmpty());
    }

    @Test
    @DisplayName("Test MetricsBaseline fromSamples")
    void testMetricsBaselineFromSamples() {
        double[] samples = new double[100];
        for (int i = 0; i < 100; i++) {
            samples[i] = 50.0 + (i - 50) * 0.1;
        }

        MetricsBaseline baseline = MetricsBaseline.fromSamples(samples);

        assertTrue(baseline.isInitialized());
        assertEquals(100, baseline.getSampleCount());
        assertTrue(baseline.getMean() > 45 && baseline.getMean() < 55);
        assertTrue(baseline.getUpperBound2Sigma() > baseline.getMean());
        assertTrue(baseline.getLowerBound2Sigma() < baseline.getMean());
        assertTrue(baseline.getUpperBound3Sigma() > baseline.getUpperBound2Sigma());
    }

    @Test
    @DisplayName("Test MetricsBaseline anomaly levels")
    void testMetricsBaselineAnomalyLevels() {
        double[] samples = new double[100];
        for (int i = 0; i < 100; i++) {
            samples[i] = 100.0;
        }
        MetricsBaseline baseline = MetricsBaseline.fromSamples(samples);

        assertEquals(MetricsBaseline.AnomalyLevel.NORMAL,
                baseline.checkAnomaly(100.0));
    }

    @Test
    @DisplayName("Test MetricsBaseline spike and drop detection")
    void testSpikeAndDropDetection() {
        double[] samples = new double[100];
        for (int i = 0; i < 100; i++) {
            samples[i] = 100.0 + Math.random() * 5;
        }
        MetricsBaseline baseline = MetricsBaseline.fromSamples(samples);

        assertFalse(baseline.isSpike(100.0));
        assertTrue(baseline.isSpike(200.0));
        assertFalse(baseline.isDrop(100.0));
    }

    @Test
    @DisplayName("Test MetricsBaseline empty samples")
    void testMetricsBaselineEmptySamples() {
        MetricsBaseline baseline = MetricsBaseline.fromSamples(new double[0]);
        assertFalse(baseline.isInitialized());
        assertEquals(0, baseline.getSampleCount());
    }

    @Test
    @DisplayName("Test RollingStats")
    void testRollingStats() {
        MetricsBaseline.RollingStats stats = new MetricsBaseline.RollingStats(100);

        stats.add(10.0);
        stats.add(20.0);
        stats.add(30.0);

        assertEquals(3, stats.getCount());
        assertEquals(20.0, stats.getMean(), 0.01);
        assertEquals(10.0, stats.getMin(), 0.01);
        assertEquals(30.0, stats.getMax(), 0.01);
    }
}

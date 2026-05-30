package com.loganalytics.functions;

import com.loganalytics.model.MetricsResult;
import com.loganalytics.model.TrafficForecast;
import org.apache.flink.streaming.api.operators.StreamProcessOperator;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.Queue;

import static org.junit.Assert.*;

public class TrafficForecasterTest {

    private KeyedOneInputStreamOperatorTestHarness<String, MetricsResult, TrafficForecast> testHarness;

    @Before
    public void setUp() throws Exception {
        TrafficForecaster forecaster = new TrafficForecaster(60, 0.3);
        testHarness = new KeyedOneInputStreamOperatorTestHarness<>(
                new StreamProcessOperator<>(forecaster),
                metrics -> metrics.getDimension() + ":" + metrics.getValue(),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(String.class),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(MetricsResult.class),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(TrafficForecast.class)
        );
        testHarness.open();
    }

    @After
    public void tearDown() throws Exception {
        testHarness.close();
    }

    @Test
    public void testNoForecastBeforeMinimumData() throws Exception {
        MetricsResult m = createMetrics(100.0);
        testHarness.processElement(new StreamRecord<>(m));

        Queue<?> output = testHarness.getOutput();
        assertTrue(output.isEmpty());
    }

    @Test
    public void testForecastAfterMinimumData() throws Exception {
        for (int i = 0; i < 6; i++) {
            MetricsResult m = createMetrics(100.0 + i * 10);
            testHarness.processElement(new StreamRecord<>(m));
        }

        Queue<StreamRecord<TrafficForecast>> output = (Queue) testHarness.getOutput();
        assertFalse(output.isEmpty());

        TrafficForecast forecast = output.poll().getValue();
        assertNotNull(forecast.getTrendDirection());
        assertTrue(forecast.getPredictedQps() >= 0);
        assertTrue(forecast.getConfidence() >= 0);
    }

    @Test
    public void testUpwardTrendDetection() throws Exception {
        for (int i = 0; i < 10; i++) {
            MetricsResult m = createMetrics(100.0 + i * 20);
            testHarness.processElement(new StreamRecord<>(m));
        }

        Queue<StreamRecord<TrafficForecast>> output = (Queue) testHarness.getOutput();
        TrafficForecast forecast = output.poll().getValue();

        assertEquals("UP", forecast.getTrendDirection());
        assertTrue(forecast.getTrendSlope() > 0);
        assertTrue(forecast.getPredictedQpsNext() > forecast.getPredictedQps());
    }

    @Test
    public void testStableTrendDetection() throws Exception {
        for (int i = 0; i < 10; i++) {
            MetricsResult m = createMetrics(500.0 + Math.sin(i) * 0.1);
            testHarness.processElement(new StreamRecord<>(m));
        }

        Queue<StreamRecord<TrafficForecast>> output = (Queue) testHarness.getOutput();
        TrafficForecast forecast = output.poll().getValue();

        assertEquals("STABLE", forecast.getTrendDirection());
    }

    @Test
    public void testMovingAverages() throws Exception {
        for (int i = 0; i < 10; i++) {
            MetricsResult m = createMetrics(100.0 + i * 10);
            testHarness.processElement(new StreamRecord<>(m));
        }

        Queue<StreamRecord<TrafficForecast>> output = (Queue) testHarness.getOutput();
        TrafficForecast forecast = output.poll().getValue();

        assertTrue(forecast.getMovingAvg5() > 0);
        assertTrue(forecast.getMovingAvg10() > 0);
        assertTrue(forecast.getMovingAvg5() > forecast.getMovingAvg10());
    }

    @Test
    public void testPredictedQpsNeverNegative() throws Exception {
        for (int i = 0; i < 10; i++) {
            MetricsResult m = createMetrics(10.0 - i * 5);
            testHarness.processElement(new StreamRecord<>(m));
        }

        Queue<StreamRecord<TrafficForecast>> output = (Queue) testHarness.getOutput();
        TrafficForecast forecast = output.poll().getValue();

        assertTrue(forecast.getPredictedQps() >= 0);
        assertTrue(forecast.getPredictedQpsNext() >= 0);
        assertTrue(forecast.getPredictedQpsNext2() >= 0);
    }

    private MetricsResult createMetrics(double qps) {
        return MetricsResult.builder()
                .dimension("all")
                .value("total")
                .qps(qps)
                .windowStart(System.currentTimeMillis() - 60000)
                .windowEnd(System.currentTimeMillis())
                .totalRequests((long) (qps * 60))
                .errorRequests(0)
                .errorRate(0.0)
                .avgLatency(100.0)
                .minLatency(50.0)
                .maxLatency(200.0)
                .stdDevLatency(30.0)
                .variance(900.0)
                .p50Latency(95.0)
                .p95Latency(180.0)
                .p99Latency(195.0)
                .p999Latency(199.0)
                .errorRateMean(2.0)
                .errorRateStdDev(1.0)
                .latencyMean(100.0)
                .latencyStdDev(30.0)
                .qpsMean(qps)
                .qpsStdDev(10.0)
                .timestamp(System.currentTimeMillis())
                .build();
    }
}

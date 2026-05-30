package com.loganalytics.functions;

import com.loganalytics.model.CustomMetric;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.util.Collector;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class CustomMetricCalculatorTest {

    @Test
    public void testCustomMetricCalculation() {
        List<CustomMetricCalculator.MetricDefinition> defs = new ArrayList<>();
        defs.add(new CustomMetricCalculator.MetricDefinition("error_burst", "error_rate*qps/100"));
        defs.add(new CustomMetricCalculator.MetricDefinition("tail_ratio", "p99_latency/p50_latency"));

        CustomMetricCalculator calculator = new CustomMetricCalculator(defs);

        List<CustomMetric> results = new ArrayList<>();
        Collector<CustomMetric> collector = new ListCollector<>(results);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/api/v1/users")
                .errorRate(5.0)
                .qps(1000.0)
                .p50Latency(50.0)
                .p95Latency(180.0)
                .p99Latency(200.0)
                .p999Latency(250.0)
                .avgLatency(100.0)
                .minLatency(10.0)
                .maxLatency(300.0)
                .stdDevLatency(30.0)
                .variance(900.0)
                .totalRequests(60000)
                .errorRequests(3000)
                .errorRateMean(3.0)
                .errorRateStdDev(1.5)
                .latencyMean(95.0)
                .latencyStdDev(25.0)
                .qpsMean(950.0)
                .qpsStdDev(100.0)
                .timestamp(System.currentTimeMillis())
                .build();

        calculator.flatMap(metrics, collector);

        assertEquals(2, results.size());

        CustomMetric errorBurst = results.stream()
                .filter(m -> m.getMetricName().equals("error_burst"))
                .findFirst().orElse(null);
        assertNotNull(errorBurst);
        assertEquals(50.0, errorBurst.getResult(), 0.01);

        CustomMetric tailRatio = results.stream()
                .filter(m -> m.getMetricName().equals("tail_ratio"))
                .findFirst().orElse(null);
        assertNotNull(tailRatio);
        assertEquals(4.0, tailRatio.getResult(), 0.01);
    }

    @Test
    public void testParseDefinitions() {
        String config = "error_burst=error_rate*qps/100;latency_cv=stddev_latency/avg_latency;tail_ratio=p99_latency/p50_latency";
        List<CustomMetricCalculator.MetricDefinition> defs = CustomMetricCalculator.parseDefinitions(config);

        assertEquals(3, defs.size());
        assertEquals("error_burst", defs.get(0).getName());
        assertEquals("latency_cv", defs.get(1).getName());
        assertEquals("tail_ratio", defs.get(2).getName());
    }

    @Test
    public void testParseDefinitionsEmpty() {
        List<CustomMetricCalculator.MetricDefinition> defs = CustomMetricCalculator.parseDefinitions("");
        assertTrue(defs.isEmpty());

        List<CustomMetricCalculator.MetricDefinition> nullDefs = CustomMetricCalculator.parseDefinitions(null);
        assertTrue(nullDefs.isEmpty());
    }

    @Test
    public void testNaNResultSkipped() {
        List<CustomMetricCalculator.MetricDefinition> defs = new ArrayList<>();
        defs.add(new CustomMetricCalculator.MetricDefinition("zero_div", "0/0"));

        CustomMetricCalculator calculator = new CustomMetricCalculator(defs);
        List<CustomMetric> results = new ArrayList<>();
        Collector<CustomMetric> collector = new ListCollector<>(results);

        MetricsResult metrics = MetricsResult.builder()
                .dimension("api")
                .value("/test")
                .errorRate(0.0)
                .qps(0.0)
                .avgLatency(0.0)
                .stdDevLatency(0.0)
                .minLatency(0.0)
                .maxLatency(0.0)
                .variance(0.0)
                .p50Latency(0.0)
                .p95Latency(0.0)
                .p99Latency(0.0)
                .p999Latency(0.0)
                .totalRequests(0)
                .errorRequests(0)
                .errorRateMean(0.0)
                .errorRateStdDev(0.0)
                .latencyMean(0.0)
                .latencyStdDev(0.0)
                .qpsMean(0.0)
                .qpsStdDev(0.0)
                .timestamp(System.currentTimeMillis())
                .build();

        calculator.flatMap(metrics, collector);
        assertEquals(0, results.size());
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

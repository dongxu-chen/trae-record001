package com.loganalytics.functions;

import com.loganalytics.aggregate.MetricsAccumulator;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

public class MetricsResultWindowFunction extends ProcessWindowFunction<MetricsAccumulator, MetricsResult, String, TimeWindow> {

    private transient ValueState<HistoricalStats> errorRateStatsState;
    private transient ValueState<HistoricalStats> latencyStatsState;
    private transient ValueState<HistoricalStats> qpsStatsState;

    private final int historyWindowSize;

    public MetricsResultWindowFunction() {
        this(30);
    }

    public MetricsResultWindowFunction(int historyWindowSize) {
        this.historyWindowSize = historyWindowSize;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<HistoricalStats> errorRateStatsDesc = new ValueStateDescriptor<>(
                "errorRateStats", TypeInformation.of(HistoricalStats.class));
        errorRateStatsState = getRuntimeContext().getState(errorRateStatsDesc);

        ValueStateDescriptor<HistoricalStats> latencyStatsDesc = new ValueStateDescriptor<>(
                "latencyStats", TypeInformation.of(HistoricalStats.class));
        latencyStatsState = getRuntimeContext().getState(latencyStatsDesc);

        ValueStateDescriptor<HistoricalStats> qpsStatsDesc = new ValueStateDescriptor<>(
                "qpsStats", TypeInformation.of(HistoricalStats.class));
        qpsStatsState = getRuntimeContext().getState(qpsStatsDesc);
    }

    @Override
    public void process(String key, Context context, Iterable<MetricsAccumulator> elements, Collector<MetricsResult> out) throws Exception {
        MetricsAccumulator accumulator = elements.iterator().next();

        if (accumulator.getTotalRequests() == 0) {
            return;
        }

        String[] keyParts = key.split(":", 2);
        String dimension = keyParts.length > 1 ? keyParts[0] : "unknown";
        String value = keyParts.length > 1 ? keyParts[1] : key;

        TimeWindow window = context.window();
        long windowDuration = window.getEnd() - window.getStart();
        double qps = (accumulator.getTotalRequests() * 1000.0) / windowDuration;

        HistoricalStats errorRateStats = updateStats(errorRateStatsState, accumulator.getErrorRate());
        HistoricalStats latencyStats = updateStats(latencyStatsState, accumulator.getMean());
        HistoricalStats qpsStats = updateStats(qpsStatsState, qps);

        MetricsResult result = MetricsResult.builder()
                .dimension(dimension)
                .value(value)
                .windowStart(window.getStart())
                .windowEnd(window.getEnd())
                .totalRequests(accumulator.getTotalRequests())
                .errorRequests(accumulator.getErrorRequests())
                .errorRate(accumulator.getErrorRate())
                .qps(qps)
                .avgLatency(accumulator.getMean())
                .minLatency(accumulator.getMinLatency())
                .maxLatency(accumulator.getMaxLatency())
                .stdDevLatency(accumulator.getStdDev())
                .variance(accumulator.getVariance())
                .p50Latency(accumulator.getP50())
                .p95Latency(accumulator.getP95())
                .p99Latency(accumulator.getP99())
                .p999Latency(accumulator.getP999())
                .timestamp(System.currentTimeMillis())
                .errorRateMean(errorRateStats.getMean())
                .errorRateStdDev(errorRateStats.getStdDev())
                .latencyMean(latencyStats.getMean())
                .latencyStdDev(latencyStats.getStdDev())
                .qpsMean(qpsStats.getMean())
                .qpsStdDev(qpsStats.getStdDev())
                .build();

        out.collect(result);
    }

    private HistoricalStats updateStats(ValueState<HistoricalStats> state, double newValue) throws Exception {
        HistoricalStats stats = state.value();
        if (stats == null) {
            stats = new HistoricalStats(historyWindowSize);
        }
        stats.add(newValue);
        state.update(stats);
        return stats;
    }

    public static class HistoricalStats implements java.io.Serializable {
        private final int maxSize;
        private final double[] values;
        private int count = 0;
        private int index = 0;
        private double sum = 0.0;
        private double sumOfSquares = 0.0;

        public HistoricalStats(int maxSize) {
            this.maxSize = maxSize;
            this.values = new double[maxSize];
        }

        public void add(double value) {
            if (count == maxSize) {
                sum -= values[index];
                sumOfSquares -= values[index] * values[index];
            } else {
                count++;
            }

            values[index] = value;
            sum += value;
            sumOfSquares += value * value;
            index = (index + 1) % maxSize;
        }

        public double getMean() {
            return count > 0 ? sum / count : 0.0;
        }

        public double getVariance() {
            if (count <= 1) {
                return 0.0;
            }
            double mean = getMean();
            return (sumOfSquares - count * mean * mean) / (count - 1);
        }

        public double getStdDev() {
            return Math.sqrt(getVariance());
        }

        public int getCount() {
            return count;
        }
    }
}

package com.loganalytics.functions;

import com.loganalytics.model.MetricsResult;
import com.loganalytics.model.TrafficForecast;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TrafficForecaster extends KeyedProcessFunction<String, MetricsResult, TrafficForecast> {

    private static final Logger LOG = LoggerFactory.getLogger(TrafficForecaster.class);

    private final int historySize;
    private final double minConfidenceThreshold;

    private transient ValueState<QpsHistory> qpsHistoryState;

    public TrafficForecaster(int historySize, double minConfidenceThreshold) {
        this.historySize = historySize;
        this.minConfidenceThreshold = minConfidenceThreshold;
    }

    public TrafficForecaster(int historySize) {
        this(historySize, 0.3);
    }

    public TrafficForecaster() {
        this(60, 0.3);
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<QpsHistory> desc = new ValueStateDescriptor<>(
                "qpsHistory", TypeInformation.of(QpsHistory.class));
        qpsHistoryState = getRuntimeContext().getState(desc);
    }

    @Override
    public void processElement(MetricsResult metrics, Context ctx, Collector<TrafficForecast> out) throws Exception {
        QpsHistory history = qpsHistoryState.value();
        if (history == null) {
            history = new QpsHistory(historySize);
        }

        history.add(metrics.getQps());
        qpsHistoryState.update(history);

        if (history.getCount() < 5) {
            return;
        }

        LinearRegressionResult regression = computeLinearRegression(history);
        double movingAvg5 = history.getMovingAverage(5);
        double movingAvg10 = history.getMovingAverage(10);

        double nextIdx = history.getCount();
        double predictedQps = regression.slope * nextIdx + regression.intercept;
        double predictedQpsNext = regression.slope * (nextIdx + 1) + regression.intercept;
        double predictedQpsNext2 = regression.slope * (nextIdx + 2) + regression.intercept;

        predictedQps = Math.max(0, predictedQps);
        predictedQpsNext = Math.max(0, predictedQpsNext);
        predictedQpsNext2 = Math.max(0, predictedQpsNext2);

        double deviation = metrics.getQps() - predictedQps;
        double deviationFromPredicted = regression.stdError > 0
                ? deviation / regression.stdError : 0.0;

        String trendDirection;
        if (Math.abs(regression.slope) < 0.01 * regression.intercept) {
            trendDirection = "STABLE";
        } else if (regression.slope > 0) {
            trendDirection = "UP";
        } else {
            trendDirection = "DOWN";
        }

        double confidence = computeConfidence(regression, history.getCount());

        TrafficForecast forecast = TrafficForecast.builder()
                .dimension(metrics.getDimension())
                .value(metrics.getValue())
                .currentQps(metrics.getQps())
                .predictedQps(predictedQps)
                .predictedQpsNext(predictedQpsNext)
                .predictedQpsNext2(predictedQpsNext2)
                .confidence(confidence)
                .trendSlope(regression.slope)
                .trendIntercept(regression.intercept)
                .trendDirection(trendDirection)
                .movingAvg5(movingAvg5)
                .movingAvg10(movingAvg10)
                .deviationFromPredicted(deviationFromPredicted)
                .windowStart(metrics.getWindowStart())
                .windowEnd(metrics.getWindowEnd())
                .timestamp(System.currentTimeMillis())
                .build();

        out.collect(forecast);
    }

    private LinearRegressionResult computeLinearRegression(QpsHistory history) {
        int n = history.getCount();
        double[] values = history.getRecentValues(n);

        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < n; i++) {
            sumX += i;
            sumY += values[i];
            sumXY += i * values[i];
            sumX2 += (double) i * i;
        }

        double xMean = sumX / n;
        double yMean = sumY / n;

        double slope;
        double intercept;
        double denom = sumX2 - n * xMean * xMean;
        if (Math.abs(denom) < 1e-10) {
            slope = 0.0;
            intercept = yMean;
        } else {
            slope = (sumXY - n * xMean * yMean) / denom;
            intercept = yMean - slope * xMean;
        }

        double ssRes = 0;
        for (int i = 0; i < n; i++) {
            double predicted = slope * i + intercept;
            ssRes += (values[i] - predicted) * (values[i] - predicted);
        }
        double stdError = n > 2 ? Math.sqrt(ssRes / (n - 2)) : 0.0;

        return new LinearRegressionResult(slope, intercept, stdError);
    }

    private double computeConfidence(LinearRegressionResult regression, int dataPoints) {
        if (dataPoints < 5) {
            return 0.0;
        }
        double baseConfidence = Math.min(1.0, (double) dataPoints / historySize);
        double errorFactor = regression.intercept > 0
                ? Math.max(0, 1.0 - regression.stdError / regression.intercept)
                : 0.0;
        return Math.max(minConfidenceThreshold, baseConfidence * errorFactor);
    }

    private static class LinearRegressionResult implements java.io.Serializable {
        final double slope;
        final double intercept;
        final double stdError;

        LinearRegressionResult(double slope, double intercept, double stdError) {
            this.slope = slope;
            this.intercept = intercept;
            this.stdError = stdError;
        }
    }

    public static class QpsHistory implements java.io.Serializable {
        private final int maxSize;
        private final double[] values;
        private int count = 0;
        private int index = 0;

        public QpsHistory(int maxSize) {
            this.maxSize = maxSize;
            this.values = new double[maxSize];
        }

        public void add(double value) {
            if (count < maxSize) {
                count++;
            }
            values[index] = value;
            index = (index + 1) % maxSize;
        }

        public double[] getRecentValues(int n) {
            int len = Math.min(n, count);
            double[] result = new double[len];
            int start = (index - len + maxSize) % maxSize;
            for (int i = 0; i < len; i++) {
                result[i] = values[(start + i) % maxSize];
            }
            return result;
        }

        public double getMovingAverage(int windowSize) {
            if (count == 0) {
                return 0.0;
            }
            int size = Math.min(windowSize, count);
            double sum = 0;
            for (int i = 0; i < size; i++) {
                int idx = (index - 1 - i + maxSize) % maxSize;
                sum += values[idx];
            }
            return sum / size;
        }

        public int getCount() {
            return count;
        }
    }
}

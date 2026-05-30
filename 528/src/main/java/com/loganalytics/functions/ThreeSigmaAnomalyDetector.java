package com.loganalytics.functions;

import com.loganalytics.model.AlertEvent;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.api.common.functions.FlatMapFunction;
import org.apache.flink.util.Collector;

import java.util.ArrayList;
import java.util.List;

public class ThreeSigmaAnomalyDetector implements FlatMapFunction<MetricsResult, AlertEvent> {

    private final double sigmaMultiplier;
    private final int minHistorySize;

    public ThreeSigmaAnomalyDetector() {
        this(3.0, 10);
    }

    public ThreeSigmaAnomalyDetector(double sigmaMultiplier, int minHistorySize) {
        this.sigmaMultiplier = sigmaMultiplier;
        this.minHistorySize = minHistorySize;
    }

    @Override
    public void flatMap(MetricsResult metrics, Collector<AlertEvent> out) {
        List<AlertEvent> alerts = new ArrayList<>();

        detectErrorRateAnomaly(metrics, alerts);
        detectLatencyAnomaly(metrics, alerts);
        detectQpsAnomaly(metrics, alerts);

        alerts.forEach(out::collect);
    }

    private void detectErrorRateAnomaly(MetricsResult metrics, List<AlertEvent> alerts) {
        double currentValue = metrics.getErrorRate();
        double mean = metrics.getErrorRateMean();
        double stdDev = metrics.getErrorRateStdDev();

        if (hasEnoughHistory(mean, stdDev)) {
            double upperBound = mean + sigmaMultiplier * stdDev;

            if (currentValue > upperBound) {
                double deviation = stdDev > 0 ? (currentValue - mean) / stdDev : 0;
                alerts.add(AlertEvent.builder()
                        .alertType("ERROR_RATE_ANOMALY")
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(upperBound)
                        .severity(getSeverity(deviation))
                        .message(String.format(
                                "Error rate anomaly detected: %.2f%% (μ=%.2f%%, σ=%.2f%%, 3σ=%.2f%%, deviation=%.2fσ) on %s:%s",
                                currentValue, mean, stdDev, upperBound, deviation,
                                metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        } else {
            double staticThreshold = 5.0;
            if (currentValue > staticThreshold) {
                alerts.add(AlertEvent.builder()
                        .alertType("ERROR_RATE_STATIC")
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(staticThreshold)
                        .severity("INFO")
                        .message(String.format(
                                "High error rate detected: %.2f%% (static threshold: %.2f%%, insufficient history for dynamic) on %s:%s",
                                currentValue, staticThreshold, metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        }
    }

    private void detectLatencyAnomaly(MetricsResult metrics, List<AlertEvent> alerts) {
        double currentValue = metrics.getP99Latency();
        double mean = metrics.getLatencyMean();
        double stdDev = metrics.getLatencyStdDev();

        if (hasEnoughHistory(mean, stdDev)) {
            double upperBound = mean + sigmaMultiplier * stdDev;

            if (currentValue > upperBound) {
                double deviation = stdDev > 0 ? (currentValue - mean) / stdDev : 0;
                alerts.add(AlertEvent.builder()
                        .alertType("LATENCY_ANOMALY")
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(upperBound)
                        .severity(getSeverity(deviation))
                        .message(String.format(
                                "P99 latency anomaly detected: %.2fms (μ=%.2fms, σ=%.2fms, 3σ=%.2fms, deviation=%.2fσ) on %s:%s",
                                currentValue, mean, stdDev, upperBound, deviation,
                                metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        } else {
            double staticThreshold = 1000.0;
            if (currentValue > staticThreshold) {
                alerts.add(AlertEvent.builder()
                        .alertType("LATENCY_STATIC")
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(staticThreshold)
                        .severity("INFO")
                        .message(String.format(
                                "High P99 latency detected: %.2fms (static threshold: %.2fms, insufficient history for dynamic) on %s:%s",
                                currentValue, staticThreshold, metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        }
    }

    private void detectQpsAnomaly(MetricsResult metrics, List<AlertEvent> alerts) {
        double currentValue = metrics.getQps();
        double mean = metrics.getQpsMean();
        double stdDev = metrics.getQpsStdDev();

        if (hasEnoughHistory(mean, stdDev)) {
            double upperBound = mean + sigmaMultiplier * stdDev;
            double lowerBound = Math.max(0, mean - sigmaMultiplier * stdDev);

            boolean isSpike = currentValue > upperBound;
            boolean isDrop = currentValue < lowerBound;

            if (isSpike || isDrop) {
                double deviation = stdDev > 0 ? (currentValue - mean) / stdDev : 0;
                String alertType = isSpike ? "QPS_SPIKE" : "QPS_DROP";
                double threshold = isSpike ? upperBound : lowerBound;
                String direction = isSpike ? "spike" : "drop";

                alerts.add(AlertEvent.builder()
                        .alertType(alertType)
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(threshold)
                        .severity(getSeverity(Math.abs(deviation)))
                        .message(String.format(
                                "QPS %s detected: %.2f (μ=%.2f, σ=%.2f, bounds=[%.2f, %.2f], deviation=%.2fσ) on %s:%s",
                                direction, currentValue, mean, stdDev, lowerBound, upperBound, deviation,
                                metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        } else {
            double staticThreshold = 10000.0;
            if (currentValue > staticThreshold) {
                alerts.add(AlertEvent.builder()
                        .alertType("QPS_STATIC")
                        .dimension(metrics.getDimension())
                        .value(metrics.getValue())
                        .currentValue(currentValue)
                        .threshold(staticThreshold)
                        .severity("INFO")
                        .message(String.format(
                                "High QPS detected: %.2f (static threshold: %.0f, insufficient history for dynamic) on %s:%s",
                                currentValue, staticThreshold, metrics.getDimension(), metrics.getValue()))
                        .timestamp(System.currentTimeMillis())
                        .build());
            }
        }
    }

    private boolean hasEnoughHistory(double mean, double stdDev) {
        return mean > 0 && stdDev > 0;
    }

    private String getSeverity(double deviation) {
        if (deviation >= 5.0) return "CRITICAL";
        if (deviation >= 3.0) return "WARNING";
        return "INFO";
    }
}

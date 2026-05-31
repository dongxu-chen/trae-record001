package com.tracing.optimizer.core.model;

import java.time.Instant;

public class TraceMetrics {

    private String serviceName;
    private long totalSpans;
    private long sampledSpans;
    private long errorSpans;
    private double currentSamplingRate;
    private double p50LatencyMs;
    private double p95LatencyMs;
    private double p99LatencyMs;
    private double errorRate;
    private long throughputPerSecond;
    private Instant collectedAt;

    public TraceMetrics() {
        this.collectedAt = Instant.now();
    }

    public double getEffectiveSamplingRate() {
        if (totalSpans == 0) return 0.0;
        return (double) sampledSpans / totalSpans;
    }

    public double getErrorRate() {
        if (totalSpans == 0) return 0.0;
        return (double) errorSpans / totalSpans;
    }

    public String getServiceName() { return serviceName; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }

    public long getTotalSpans() { return totalSpans; }
    public void setTotalSpans(long totalSpans) { this.totalSpans = totalSpans; }

    public long getSampledSpans() { return sampledSpans; }
    public void setSampledSpans(long sampledSpans) { this.sampledSpans = sampledSpans; }

    public long getErrorSpans() { return errorSpans; }
    public void setErrorSpans(long errorSpans) { this.errorSpans = errorSpans; }

    public double getCurrentSamplingRate() { return currentSamplingRate; }
    public void setCurrentSamplingRate(double currentSamplingRate) { this.currentSamplingRate = currentSamplingRate; }

    public double getP50LatencyMs() { return p50LatencyMs; }
    public void setP50LatencyMs(double p50LatencyMs) { this.p50LatencyMs = p50LatencyMs; }

    public double getP95LatencyMs() { return p95LatencyMs; }
    public void setP95LatencyMs(double p95LatencyMs) { this.p95LatencyMs = p95LatencyMs; }

    public double getP99LatencyMs() { return p99LatencyMs; }
    public void setP99LatencyMs(double p99LatencyMs) { this.p99LatencyMs = p99LatencyMs; }

    public void setErrorRate(double errorRate) { this.errorRate = errorRate; }

    public long getThroughputPerSecond() { return throughputPerSecond; }
    public void setThroughputPerSecond(long throughputPerSecond) { this.throughputPerSecond = throughputPerSecond; }

    public Instant getCollectedAt() { return collectedAt; }
    public void setCollectedAt(Instant collectedAt) { this.collectedAt = collectedAt; }
}

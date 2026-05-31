package com.tracing.optimizer.core.model;

import java.time.Instant;
import java.util.Objects;

public class SamplingRate {

    private String serviceName;
    private double rate;
    private double previousRate;
    private String reason;
    private Instant effectiveTime;
    private boolean isEdgeOptimized;
    private double confidenceScore;

    public SamplingRate() {
        this.effectiveTime = Instant.now();
        this.isEdgeOptimized = false;
        this.confidenceScore = 1.0;
    }

    public SamplingRate(String serviceName, double rate, String reason) {
        this.serviceName = serviceName;
        this.rate = Math.max(0.0, Math.min(1.0, rate));
        this.reason = reason;
        this.effectiveTime = Instant.now();
        this.isEdgeOptimized = false;
        this.confidenceScore = 1.0;
    }

    public boolean isSignificantChange(double threshold) {
        return Math.abs(rate - previousRate) > threshold;
    }

    public String getServiceName() { return serviceName; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }

    public double getRate() { return rate; }
    public void setRate(double rate) { this.rate = Math.max(0.0, Math.min(1.0, rate)); }

    public double getPreviousRate() { return previousRate; }
    public void setPreviousRate(double previousRate) { this.previousRate = previousRate; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }

    public Instant getEffectiveTime() { return effectiveTime; }
    public void setEffectiveTime(Instant effectiveTime) { this.effectiveTime = effectiveTime; }

    public boolean isEdgeOptimized() { return isEdgeOptimized; }
    public void setEdgeOptimized(boolean edgeOptimized) { isEdgeOptimized = edgeOptimized; }

    public double getConfidenceScore() { return confidenceScore; }
    public void setConfidenceScore(double confidenceScore) { this.confidenceScore = confidenceScore; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof SamplingRate)) return false;
        SamplingRate that = (SamplingRate) o;
        return Objects.equals(serviceName, that.serviceName)
                && Objects.equals(effectiveTime, that.effectiveTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serviceName, effectiveTime);
    }
}

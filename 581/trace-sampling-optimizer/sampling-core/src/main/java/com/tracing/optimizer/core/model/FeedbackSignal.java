package com.tracing.optimizer.core.model;

import java.time.Instant;

public class FeedbackSignal {

    public enum SignalType {
        ERROR_RATE_INCREASED,
        LATENCY_DEGRADED,
        MISSING_CRITICAL_TRACE,
        FALSE_POSITIVE_ANOMALY,
        COST_OVERRUN,
        OBSERVABILITY_GAP,
        SAMPLING_EFFECTIVE
    }

    private String serviceName;
    private SignalType signalType;
    private double severity;
    private String description;
    private Instant timestamp;
    private double previousSamplingRate;
    private double suggestedRate;

    public FeedbackSignal() {
        this.timestamp = Instant.now();
    }

    public FeedbackSignal(String serviceName, SignalType signalType, double severity, String description) {
        this.serviceName = serviceName;
        this.signalType = signalType;
        this.severity = Math.max(0.0, Math.min(1.0, severity));
        this.description = description;
        this.timestamp = Instant.now();
    }

    public String getServiceName() { return serviceName; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }

    public SignalType getSignalType() { return signalType; }
    public void setSignalType(SignalType signalType) { this.signalType = signalType; }

    public double getSeverity() { return severity; }
    public void setSeverity(double severity) { this.severity = Math.max(0.0, Math.min(1.0, severity)); }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }

    public double getPreviousSamplingRate() { return previousSamplingRate; }
    public void setPreviousSamplingRate(double previousSamplingRate) { this.previousSamplingRate = previousSamplingRate; }

    public double getSuggestedRate() { return suggestedRate; }
    public void setSuggestedRate(double suggestedRate) { this.suggestedRate = suggestedRate; }
}

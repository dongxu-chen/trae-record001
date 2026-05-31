package com.tracing.optimizer.core.model;

import java.util.Map;
import java.util.Objects;

public class ServiceMetadata {

    private String serviceName;
    private String serviceNamespace;
    private double businessImportance;
    private double errorRate;
    private double p99LatencyMs;
    private double p95LatencyMs;
    private double avgLatencyMs;
    private long requestRate;
    private Map<String, String> tags;
    private long lastUpdatedEpochMs;

    public ServiceMetadata() {}

    public ServiceMetadata(String serviceName, double businessImportance, double errorRate,
                           double p99LatencyMs, long requestRate) {
        this.serviceName = serviceName;
        this.businessImportance = businessImportance;
        this.errorRate = errorRate;
        this.p99LatencyMs = p99LatencyMs;
        this.requestRate = requestRate;
        this.lastUpdatedEpochMs = System.currentTimeMillis();
    }

    public double computePriorityScore() {
        double importanceWeight = 0.4;
        double errorWeight = 0.35;
        double latencyWeight = 0.25;
        double normalizedLatency = Math.min(p99LatencyMs / 5000.0, 1.0);
        return importanceWeight * businessImportance
                + errorWeight * errorRate
                + latencyWeight * normalizedLatency;
    }

    public String getServiceName() { return serviceName; }
    public void setServiceName(String serviceName) { this.serviceName = serviceName; }

    public String getServiceNamespace() { return serviceNamespace; }
    public void setServiceNamespace(String serviceNamespace) { this.serviceNamespace = serviceNamespace; }

    public double getBusinessImportance() { return businessImportance; }
    public void setBusinessImportance(double businessImportance) { this.businessImportance = businessImportance; }

    public double getErrorRate() { return errorRate; }
    public void setErrorRate(double errorRate) { this.errorRate = errorRate; }

    public double getP99LatencyMs() { return p99LatencyMs; }
    public void setP99LatencyMs(double p99LatencyMs) { this.p99LatencyMs = p99LatencyMs; }

    public double getP95LatencyMs() { return p95LatencyMs; }
    public void setP95LatencyMs(double p95LatencyMs) { this.p95LatencyMs = p95LatencyMs; }

    public double getAvgLatencyMs() { return avgLatencyMs; }
    public void setAvgLatencyMs(double avgLatencyMs) { this.avgLatencyMs = avgLatencyMs; }

    public long getRequestRate() { return requestRate; }
    public void setRequestRate(long requestRate) { this.requestRate = requestRate; }

    public Map<String, String> getTags() { return tags; }
    public void setTags(Map<String, String> tags) { this.tags = tags; }

    public long getLastUpdatedEpochMs() { return lastUpdatedEpochMs; }
    public void setLastUpdatedEpochMs(long lastUpdatedEpochMs) { this.lastUpdatedEpochMs = lastUpdatedEpochMs; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof ServiceMetadata)) return false;
        ServiceMetadata that = (ServiceMetadata) o;
        return Objects.equals(serviceName, that.serviceName)
                && Objects.equals(serviceNamespace, that.serviceNamespace);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serviceName, serviceNamespace);
    }
}

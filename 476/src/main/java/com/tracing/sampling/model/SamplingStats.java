package com.tracing.sampling.model;

public class SamplingStats {
    private long totalRequests;
    private long sampledRequests;
    private long highLatencySampled;
    private long errorSampled;
    private long parentSampled;
    private double currentSampleRate;
    private long lastResetTime;

    public SamplingStats() {
    }

    public SamplingStats(long totalRequests, long sampledRequests, long highLatencySampled,
                         long errorSampled, long parentSampled, double currentSampleRate, long lastResetTime) {
        this.totalRequests = totalRequests;
        this.sampledRequests = sampledRequests;
        this.highLatencySampled = highLatencySampled;
        this.errorSampled = errorSampled;
        this.parentSampled = parentSampled;
        this.currentSampleRate = currentSampleRate;
        this.lastResetTime = lastResetTime;
    }

    public long getTotalRequests() {
        return totalRequests;
    }

    public void setTotalRequests(long totalRequests) {
        this.totalRequests = totalRequests;
    }

    public long getSampledRequests() {
        return sampledRequests;
    }

    public void setSampledRequests(long sampledRequests) {
        this.sampledRequests = sampledRequests;
    }

    public long getHighLatencySampled() {
        return highLatencySampled;
    }

    public void setHighLatencySampled(long highLatencySampled) {
        this.highLatencySampled = highLatencySampled;
    }

    public long getErrorSampled() {
        return errorSampled;
    }

    public void setErrorSampled(long errorSampled) {
        this.errorSampled = errorSampled;
    }

    public long getParentSampled() {
        return parentSampled;
    }

    public void setParentSampled(long parentSampled) {
        this.parentSampled = parentSampled;
    }

    public double getCurrentSampleRate() {
        return currentSampleRate;
    }

    public void setCurrentSampleRate(double currentSampleRate) {
        this.currentSampleRate = currentSampleRate;
    }

    public long getLastResetTime() {
        return lastResetTime;
    }

    public void setLastResetTime(long lastResetTime) {
        this.lastResetTime = lastResetTime;
    }

    public double getActualSampleRate() {
        if (totalRequests == 0) {
            return 0.0;
        }
        return (double) sampledRequests / totalRequests;
    }
}

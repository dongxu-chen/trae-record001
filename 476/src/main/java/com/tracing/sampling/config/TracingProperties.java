package com.tracing.sampling.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "tracing")
public class TracingProperties {

    private ServiceProperties service = new ServiceProperties();
    private SamplingProperties sampling = new SamplingProperties();
    private OtlpProperties otlp = new OtlpProperties();

    public ServiceProperties getService() {
        return service;
    }

    public void setService(ServiceProperties service) {
        this.service = service;
    }

    public SamplingProperties getSampling() {
        return sampling;
    }

    public void setSampling(SamplingProperties sampling) {
        this.sampling = sampling;
    }

    public OtlpProperties getOtlp() {
        return otlp;
    }

    public void setOtlp(OtlpProperties otlp) {
        this.otlp = otlp;
    }

    public static class ServiceProperties {
        private String name;
        private ServiceImportance importance = ServiceImportance.MEDIUM;

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public ServiceImportance getImportance() {
            return importance;
        }

        public void setImportance(ServiceImportance importance) {
            this.importance = importance;
        }
    }

    public enum ServiceImportance {
        LOW(0.5),
        MEDIUM(1.0),
        HIGH(2.0),
        CRITICAL(3.0);

        private final double multiplier;

        ServiceImportance(double multiplier) {
            this.multiplier = multiplier;
        }

        public double getMultiplier() {
            return multiplier;
        }
    }

    public static class SamplingProperties {
        private boolean enabled = true;
        private boolean consistentSamplingEnabled = true;
        private double defaultSampleRate = 0.1;
        private long highLatencyThresholdMs = 500;
        private double errorSampleRate = 1.0;
        private AdaptiveProperties adaptive = new AdaptiveProperties();

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public boolean isConsistentSamplingEnabled() {
            return consistentSamplingEnabled;
        }

        public void setConsistentSamplingEnabled(boolean consistentSamplingEnabled) {
            this.consistentSamplingEnabled = consistentSamplingEnabled;
        }

        public double getDefaultSampleRate() {
            return defaultSampleRate;
        }

        public void setDefaultSampleRate(double defaultSampleRate) {
            this.defaultSampleRate = defaultSampleRate;
        }

        public long getHighLatencyThresholdMs() {
            return highLatencyThresholdMs;
        }

        public void setHighLatencyThresholdMs(long highLatencyThresholdMs) {
            this.highLatencyThresholdMs = highLatencyThresholdMs;
        }

        public double getErrorSampleRate() {
            return errorSampleRate;
        }

        public void setErrorSampleRate(double errorSampleRate) {
            this.errorSampleRate = errorSampleRate;
        }

        public AdaptiveProperties getAdaptive() {
            return adaptive;
        }

        public void setAdaptive(AdaptiveProperties adaptive) {
            this.adaptive = adaptive;
        }
    }

    public static class AdaptiveProperties {
        private boolean enabled = true;
        private int targetSpansPerSecond = 100;
        private long adjustmentIntervalMs = 30000;
        private double minSampleRate = 0.01;
        private double maxSampleRate = 1.0;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public int getTargetSpansPerSecond() {
            return targetSpansPerSecond;
        }

        public void setTargetSpansPerSecond(int targetSpansPerSecond) {
            this.targetSpansPerSecond = targetSpansPerSecond;
        }

        public long getAdjustmentIntervalMs() {
            return adjustmentIntervalMs;
        }

        public void setAdjustmentIntervalMs(long adjustmentIntervalMs) {
            this.adjustmentIntervalMs = adjustmentIntervalMs;
        }

        public double getMinSampleRate() {
            return minSampleRate;
        }

        public void setMinSampleRate(double minSampleRate) {
            this.minSampleRate = minSampleRate;
        }

        public double getMaxSampleRate() {
            return maxSampleRate;
        }

        public void setMaxSampleRate(double maxSampleRate) {
            this.maxSampleRate = maxSampleRate;
        }
    }

    public static class OtlpProperties {
        private String endpoint = "http://localhost:4317";
        private long timeoutMs = 10000;

        public String getEndpoint() {
            return endpoint;
        }

        public void setEndpoint(String endpoint) {
            this.endpoint = endpoint;
        }

        public long getTimeoutMs() {
            return timeoutMs;
        }

        public void setTimeoutMs(long timeoutMs) {
            this.timeoutMs = timeoutMs;
        }
    }
}

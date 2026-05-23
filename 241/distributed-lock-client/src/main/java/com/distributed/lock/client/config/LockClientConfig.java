package com.distributed.lock.client.config;

import java.util.UUID;

public class LockClientConfig {
    
    private static final String DEFAULT_SERVER_HOST = "localhost";
    private static final int DEFAULT_SERVER_PORT = 50051;
    private static final long DEFAULT_TIMEOUT_MS = 30000;
    private static final long DEFAULT_LEASE_TTL_SECONDS = 30;
    private static final boolean DEFAULT_AUTO_RENEW_LEASE = true;

    private final String serverHost;
    private final int serverPort;
    private final String clientId;
    private final long defaultTimeoutMs;
    private final long defaultLeaseTtlSeconds;
    private final boolean autoRenewLease;
    
    private final int retryMaxAttempts;
    private final long retryWaitDurationMs;
    private final double circuitBreakerFailureRateThreshold;
    private final int circuitBreakerRingBufferSizeInClosedState;
    private final int circuitBreakerRingBufferSizeInHalfOpenState;
    private final long circuitBreakerWaitDurationInOpenStateMs;

    private LockClientConfig(Builder builder) {
        this.serverHost = builder.serverHost;
        this.serverPort = builder.serverPort;
        this.clientId = builder.clientId;
        this.defaultTimeoutMs = builder.defaultTimeoutMs;
        this.defaultLeaseTtlSeconds = builder.defaultLeaseTtlSeconds;
        this.autoRenewLease = builder.autoRenewLease;
        this.retryMaxAttempts = builder.retryMaxAttempts;
        this.retryWaitDurationMs = builder.retryWaitDurationMs;
        this.circuitBreakerFailureRateThreshold = builder.circuitBreakerFailureRateThreshold;
        this.circuitBreakerRingBufferSizeInClosedState = builder.circuitBreakerRingBufferSizeInClosedState;
        this.circuitBreakerRingBufferSizeInHalfOpenState = builder.circuitBreakerRingBufferSizeInHalfOpenState;
        this.circuitBreakerWaitDurationInOpenStateMs = builder.circuitBreakerWaitDurationInOpenStateMs;
    }

    public String getServerHost() {
        return serverHost;
    }

    public int getServerPort() {
        return serverPort;
    }

    public String getClientId() {
        return clientId;
    }

    public long getDefaultTimeoutMs() {
        return defaultTimeoutMs;
    }

    public long getDefaultLeaseTtlSeconds() {
        return defaultLeaseTtlSeconds;
    }

    public boolean isAutoRenewLease() {
        return autoRenewLease;
    }

    public int getRetryMaxAttempts() {
        return retryMaxAttempts;
    }

    public long getRetryWaitDurationMs() {
        return retryWaitDurationMs;
    }

    public double getCircuitBreakerFailureRateThreshold() {
        return circuitBreakerFailureRateThreshold;
    }

    public int getCircuitBreakerRingBufferSizeInClosedState() {
        return circuitBreakerRingBufferSizeInClosedState;
    }

    public int getCircuitBreakerRingBufferSizeInHalfOpenState() {
        return circuitBreakerRingBufferSizeInHalfOpenState;
    }

    public long getCircuitBreakerWaitDurationInOpenStateMs() {
        return circuitBreakerWaitDurationInOpenStateMs;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String serverHost = DEFAULT_SERVER_HOST;
        private int serverPort = DEFAULT_SERVER_PORT;
        private String clientId = UUID.randomUUID().toString();
        private long defaultTimeoutMs = DEFAULT_TIMEOUT_MS;
        private long defaultLeaseTtlSeconds = DEFAULT_LEASE_TTL_SECONDS;
        private boolean autoRenewLease = DEFAULT_AUTO_RENEW_LEASE;
        
        private int retryMaxAttempts = 3;
        private long retryWaitDurationMs = 500;
        private double circuitBreakerFailureRateThreshold = 50.0;
        private int circuitBreakerRingBufferSizeInClosedState = 10;
        private int circuitBreakerRingBufferSizeInHalfOpenState = 5;
        private long circuitBreakerWaitDurationInOpenStateMs = 10000;

        public Builder serverHost(String serverHost) {
            this.serverHost = serverHost;
            return this;
        }

        public Builder serverPort(int serverPort) {
            this.serverPort = serverPort;
            return this;
        }

        public Builder clientId(String clientId) {
            this.clientId = clientId;
            return this;
        }

        public Builder defaultTimeoutMs(long defaultTimeoutMs) {
            this.defaultTimeoutMs = defaultTimeoutMs;
            return this;
        }

        public Builder defaultLeaseTtlSeconds(long defaultLeaseTtlSeconds) {
            this.defaultLeaseTtlSeconds = defaultLeaseTtlSeconds;
            return this;
        }

        public Builder autoRenewLease(boolean autoRenewLease) {
            this.autoRenewLease = autoRenewLease;
            return this;
        }

        public Builder retryMaxAttempts(int retryMaxAttempts) {
            this.retryMaxAttempts = retryMaxAttempts;
            return this;
        }

        public Builder retryWaitDurationMs(long retryWaitDurationMs) {
            this.retryWaitDurationMs = retryWaitDurationMs;
            return this;
        }

        public Builder circuitBreakerFailureRateThreshold(double circuitBreakerFailureRateThreshold) {
            this.circuitBreakerFailureRateThreshold = circuitBreakerFailureRateThreshold;
            return this;
        }

        public Builder circuitBreakerRingBufferSizeInClosedState(int circuitBreakerRingBufferSizeInClosedState) {
            this.circuitBreakerRingBufferSizeInClosedState = circuitBreakerRingBufferSizeInClosedState;
            return this;
        }

        public Builder circuitBreakerRingBufferSizeInHalfOpenState(int circuitBreakerRingBufferSizeInHalfOpenState) {
            this.circuitBreakerRingBufferSizeInHalfOpenState = circuitBreakerRingBufferSizeInHalfOpenState;
            return this;
        }

        public Builder circuitBreakerWaitDurationInOpenStateMs(long circuitBreakerWaitDurationInOpenStateMs) {
            this.circuitBreakerWaitDurationInOpenStateMs = circuitBreakerWaitDurationInOpenStateMs;
            return this;
        }

        public LockClientConfig build() {
            return new LockClientConfig(this);
        }
    }
}
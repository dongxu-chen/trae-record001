package com.distributed.lock.server.config;

import java.util.Arrays;
import java.util.List;

public class LockServerConfig {
    
    private static final String DEFAULT_ETCD_ENDPOINTS = "http://localhost:2379";
    private static final int DEFAULT_GRPC_PORT = 50051;
    private static final long DEFAULT_LEASE_TTL_SECONDS = 30;
    private static final String DEFAULT_LOCK_PREFIX = "/distributed/locks/";

    private final List<String> etcdEndpoints;
    private final int grpcPort;
    private final long defaultLeaseTtlSeconds;
    private final String lockPrefix;
    private final boolean leaseAutoRenewEnabled;
    private final long leaseRenewIntervalSeconds;

    private LockServerConfig(Builder builder) {
        this.etcdEndpoints = builder.etcdEndpoints;
        this.grpcPort = builder.grpcPort;
        this.defaultLeaseTtlSeconds = builder.defaultLeaseTtlSeconds;
        this.lockPrefix = builder.lockPrefix;
        this.leaseAutoRenewEnabled = builder.leaseAutoRenewEnabled;
        this.leaseRenewIntervalSeconds = builder.leaseRenewIntervalSeconds;
    }

    public List<String> getEtcdEndpoints() {
        return etcdEndpoints;
    }

    public int getGrpcPort() {
        return grpcPort;
    }

    public long getDefaultLeaseTtlSeconds() {
        return defaultLeaseTtlSeconds;
    }

    public String getLockPrefix() {
        return lockPrefix;
    }

    public boolean isLeaseAutoRenewEnabled() {
        return leaseAutoRenewEnabled;
    }

    public long getLeaseRenewIntervalSeconds() {
        return leaseRenewIntervalSeconds;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private List<String> etcdEndpoints = Arrays.asList(DEFAULT_ETCD_ENDPOINTS.split(","));
        private int grpcPort = DEFAULT_GRPC_PORT;
        private long defaultLeaseTtlSeconds = DEFAULT_LEASE_TTL_SECONDS;
        private String lockPrefix = DEFAULT_LOCK_PREFIX;
        private boolean leaseAutoRenewEnabled = true;
        private long leaseRenewIntervalSeconds = DEFAULT_LEASE_TTL_SECONDS / 3;

        public Builder etcdEndpoints(List<String> etcdEndpoints) {
            this.etcdEndpoints = etcdEndpoints;
            return this;
        }

        public Builder grpcPort(int grpcPort) {
            this.grpcPort = grpcPort;
            return this;
        }

        public Builder defaultLeaseTtlSeconds(long defaultLeaseTtlSeconds) {
            this.defaultLeaseTtlSeconds = defaultLeaseTtlSeconds;
            return this;
        }

        public Builder lockPrefix(String lockPrefix) {
            this.lockPrefix = lockPrefix;
            return this;
        }

        public Builder leaseAutoRenewEnabled(boolean leaseAutoRenewEnabled) {
            this.leaseAutoRenewEnabled = leaseAutoRenewEnabled;
            return this;
        }

        public Builder leaseRenewIntervalSeconds(long leaseRenewIntervalSeconds) {
            this.leaseRenewIntervalSeconds = leaseRenewIntervalSeconds;
            return this;
        }

        public LockServerConfig build() {
            return new LockServerConfig(this);
        }
    }
}
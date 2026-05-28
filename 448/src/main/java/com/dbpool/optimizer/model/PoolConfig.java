package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolConfig {
    private PoolType poolType;
    private int maxPoolSize;
    private int minIdle;
    private long connectionTimeoutMs;
    private long idleTimeoutMs;
    private long maxLifetimeMs;
    private long leakDetectionThresholdMs;
    private String validationQuery;
    private boolean testOnBorrow;
    private boolean testOnReturn;
    private boolean testWhileIdle;
    private long timeBetweenEvictionRunsMs;
    private int numTestsPerEvictionRun;
}

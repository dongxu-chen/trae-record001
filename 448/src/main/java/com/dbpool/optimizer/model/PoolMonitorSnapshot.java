package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolMonitorSnapshot {
    private long timestamp;
    private int activeConnections;
    private int idleConnections;
    private int waitingThreads;
    private int totalConnections;
    private double avgBorrowTimeMs;
    private double maxBorrowTimeMs;
    private double avgReturnTimeMs;
    private double avgWaitTimeMs;
    private double utilization;
    private double throughputLastSecond;
    private int connectionsBorrowed;
    private int connectionsReturned;
    private int connectionTimeouts;
    private long uptimeMs;
}

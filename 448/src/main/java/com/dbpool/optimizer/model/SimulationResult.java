package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimulationResult {
    private PoolConfig config;
    private WorkloadProfile workload;
    private double avgWaitTimeMs;
    private double maxWaitTimeMs;
    private double percentile95WaitTimeMs;
    private double avgActiveConnections;
    private double avgIdleConnections;
    private double connectionUtilization;
    private double throughput;
    private int totalRequests;
    private int failedRequests;
    private int timeoutCount;
    private double rejectRate;
    private List<Double> waitTimeSamples;
    private Map<Integer, Double> utilizationOverTime;
    private QueueMetrics queueMetrics;
    private OptimizationRecommendation recommendation;
    private MixedTransactionMetrics mixedTransactionMetrics;
    private BurstinessMetrics burstinessMetrics;
}

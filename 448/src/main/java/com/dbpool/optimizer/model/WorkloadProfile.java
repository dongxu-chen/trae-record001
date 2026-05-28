package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WorkloadProfile {
    private double arrivalRate;
    private double avgServiceTimeMs;
    private double serviceTimeStdDevMs;
    private int peakConcurrentUsers;
    private double throughput;
    private long simulationDurationMs;
    private double varianceFactor;
    private MarkovArrivalConfig markovArrivalConfig;
    private MixedTransactionConfig mixedTransactionConfig;
}

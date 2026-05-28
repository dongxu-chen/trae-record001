package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OptimizationRequest {
    private PoolConfig currentConfig;
    private WorkloadProfile workload;
    private double targetWaitTimeMs;
    private double maxAllowedUtilization;
    private boolean enableCostOptimization;
    private DatabaseConstraint databaseConstraint;
}

package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueueMetrics {
    private double avgQueueLength;
    private double maxQueueLength;
    private double avgQueueWaitTimeMs;
    private double serverUtilization;
    private double probabilityOfWaiting;
    private double erlangC;
    private int effectiveServers;
    private double trafficIntensity;
    private double burstinessIndex;
    private double squaredCoefficientOfVariation;
    private double mapEffectiveArrivalRate;
}

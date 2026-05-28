package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BurstinessMetrics {
    private double burstinessIndex;
    private double squaredCoefficientOfVariation;
    private double peakArrivalRate;
    private double valleyArrivalRate;
    private double avgArrivalRate;
    private int burstCount;
    private double avgBurstDurationMs;
    private double maxBurstArrivalRate;
    private double interArrivalSquaredCV;
}

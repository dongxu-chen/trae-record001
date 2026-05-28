package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MixedTransactionMetrics {
    private int shortQueryCount;
    private int longQueryCount;
    private double shortQueryAvgWaitTimeMs;
    private double longQueryAvgWaitTimeMs;
    private double shortQueryAvgServiceTimeMs;
    private double longQueryAvgServiceTimeMs;
    private double shortQueryP95WaitTimeMs;
    private double longQueryP95WaitTimeMs;
    private double shortQueryTimeoutRate;
    private double longQueryTimeoutRate;
    private double shortQueryRatio;
}

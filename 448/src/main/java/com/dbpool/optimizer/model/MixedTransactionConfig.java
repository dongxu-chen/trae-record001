package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MixedTransactionConfig {
    private boolean enabled;
    private double shortQueryRatio;
    private double shortQueryAvgTimeMs;
    private double shortQueryStdDevMs;
    private double longQueryAvgTimeMs;
    private double longQueryStdDevMs;

    public static MixedTransactionConfig defaultConfig() {
        return MixedTransactionConfig.builder()
                .enabled(true)
                .shortQueryRatio(0.8)
                .shortQueryAvgTimeMs(30.0)
                .shortQueryStdDevMs(10.0)
                .longQueryAvgTimeMs(500.0)
                .longQueryStdDevMs(150.0)
                .build();
    }
}

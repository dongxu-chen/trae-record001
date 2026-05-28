package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarkovArrivalConfig {
    private boolean enabled;
    private int stateCount;
    private double[][] transitionMatrix;
    private double[] arrivalRates;
    private double burstinessFactor;

    public static MarkovArrivalConfig defaultConfig() {
        double[][] defaultTransition = {
                {0.7, 0.3},
                {0.4, 0.6}
        };
        double[] defaultArrivalRates = {30.0, 120.0};

        return MarkovArrivalConfig.builder()
                .enabled(true)
                .stateCount(2)
                .transitionMatrix(defaultTransition)
                .arrivalRates(defaultArrivalRates)
                .burstinessFactor(2.0)
                .build();
    }
}

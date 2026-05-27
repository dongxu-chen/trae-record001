package com.datasecurity.masking.dp;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DPQueryResult {

    private Double noisyValue;

    private Double trueValue;

    private Double epsilonUsed;

    private Double deltaUsed;

    private Double sensitivity;

    private String privacyBudgetStatus;

    private Double errorBound;

    private String operation;

    private long timestamp;

    public static DPQueryResult of(double noisyValue, double trueValue, double epsilon,
                                   double delta, double sensitivity) {
        return DPQueryResult.builder()
                .noisyValue(noisyValue)
                .trueValue(trueValue)
                .epsilonUsed(epsilon)
                .deltaUsed(delta)
                .sensitivity(sensitivity)
                .errorBound(Math.abs(noisyValue - trueValue))
                .timestamp(System.currentTimeMillis())
                .build();
    }
}

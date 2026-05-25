package com.riskcontrol.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FeatureContribution implements Serializable {
    private String featureName;
    private String featureDescription;
    private double featureValue;
    private double contribution;
    private double contributionPercent;
    private String impactDirection;
    private String category;

    public enum Category {
        DEVICE,
        IP,
        BEHAVIOR,
        HISTORY,
        CONTEXT
    }
}

package com.riskcontrol.common.model;

import com.riskcontrol.common.enums.RiskLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DecisionExplanation implements Serializable {
    private String summary;
    private String detailedExplanation;
    private RiskLevel riskLevel;
    private int finalScore;

    @Builder.Default
    private List<RuleHit> ruleContributions = new ArrayList<>();

    @Builder.Default
    private List<FeatureContribution> topFeatureContributions = new ArrayList<>();

    private double ruleScoreContribution;
    private double mlScoreContribution;
    private String decisionAction;
    private String actionReason;
    private List<String> recommendations;
    private long explanationTimestamp;

    public void addRuleContribution(RuleHit ruleHit) {
        if (this.ruleContributions == null) {
            this.ruleContributions = new ArrayList<>();
        }
        this.ruleContributions.add(ruleHit);
    }

    public void addFeatureContribution(FeatureContribution feature) {
        if (this.topFeatureContributions == null) {
            this.topFeatureContributions = new ArrayList<>();
        }
        this.topFeatureContributions.add(feature);
    }
}

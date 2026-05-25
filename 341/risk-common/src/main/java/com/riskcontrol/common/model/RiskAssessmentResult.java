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
public class RiskAssessmentResult implements Serializable {
    private String eventId;
    private String userId;
    private RiskLevel riskLevel;
    private int ruleScore;
    private int mlScore;
    private int finalScore;
    private boolean isAllowed;
    private boolean requireMfa;
    private boolean requireCaptcha;
    private boolean blockAccount;
    @Builder.Default
    private List<RuleHit> hitRules = new ArrayList<>();
    private String decisionReason;
    private long assessmentTimestamp;
    private long processingTimeMs;
    private DecisionExplanation explanation;

    public void addHitRule(RuleHit ruleHit) {
        if (this.hitRules == null) {
            this.hitRules = new ArrayList<>();
        }
        this.hitRules.add(ruleHit);
    }

    public int calculateTotalRuleScore() {
        if (hitRules == null || hitRules.isEmpty()) {
            return 0;
        }
        return hitRules.stream().mapToInt(RuleHit::getScore).sum();
    }
}

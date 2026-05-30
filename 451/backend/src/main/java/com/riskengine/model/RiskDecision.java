package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.util.List;

@Data
public class RiskDecision implements Serializable {
    private String eventId;
    private String action;
    private Integer riskScore;
    private List<String> hitRules;
    private List<String> riskTags;
    private Long decisionTime;

    public RiskDecision() {
        this.decisionTime = System.currentTimeMillis();
    }

    public enum Action {
        PASS, REVIEW, REJECT, BLOCK
    }
}

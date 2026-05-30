package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;

@Data
public class EffectEvaluation implements Serializable {
    private String ruleCode;
    private String ruleName;
    private String evaluationId;
    private Long beforeTotalEvents;
    private Long beforeHitCount;
    private Double beforeHitRate;
    private Long beforeRejectCount;
    private Double beforeRejectRate;
    private Long afterTotalEvents;
    private Long afterHitCount;
    private Double afterHitRate;
    private Long afterRejectCount;
    private Double afterRejectRate;
    private Double hitRateChange;
    private Double rejectRateChange;
    private String conclusion;
}

package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;

@Data
public class HitStats implements Serializable {
    private String ruleCode;
    private String ruleName;
    private Long totalEvents;
    private Long hitCount;
    private Double hitRate;
    private Long passCount;
    private Long reviewCount;
    private Long rejectCount;
    private Long blockCount;
    private Double avgRiskScore;
}

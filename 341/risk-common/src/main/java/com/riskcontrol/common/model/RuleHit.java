package com.riskcontrol.common.model;

import com.riskcontrol.common.enums.RuleType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleHit implements Serializable {
    private String ruleId;
    private String ruleName;
    private RuleType ruleType;
    private int score;
    private String description;
    private String evidence;
    private long hitTimestamp;
}

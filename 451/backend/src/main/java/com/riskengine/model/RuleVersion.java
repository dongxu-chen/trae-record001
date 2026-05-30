package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
public class RuleVersion implements Serializable {
    private Long id;
    private Long ruleId;
    private String ruleCode;
    private Integer version;
    private String ruleContent;
    private String droolsDrl;
    private String groovyScript;
    private String changeLog;
    private LocalDateTime createTime;
    private String operator;
}

package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.time.LocalDateTime;

@Data
public class RuleDefinition implements Serializable {
    private Long id;
    private String ruleCode;
    private String ruleName;
    private String ruleType;
    private String ruleContent;
    private String droolsDrl;
    private String groovyScript;
    private Integer priority;
    private Boolean enabled;
    private Integer version;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private String description;
    private String sceneCode;

    public RuleDefinition() {
        this.enabled = true;
        this.version = 1;
        this.priority = 100;
        this.createTime = LocalDateTime.now();
        this.updateTime = LocalDateTime.now();
    }
}

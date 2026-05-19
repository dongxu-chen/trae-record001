package com.risk.engine.rules;

import lombok.Data;

import java.util.Map;

@Data
public class RuleDefinition {

    private String ruleCode;
    private String ruleName;
    private String description;
    private String scene;
    private Integer priority;
    private Condition condition;
    private Action action;
    private String version;
    private String tags;

    @Data
    public static class Condition {
        private String type = "MVEL";
        private String expression;
        private Map<String, Object> params;
    }

    @Data
    public static class Action {
        private String type = "MVEL";
        private String expression;
        private Map<String, Object> params;
    }
}

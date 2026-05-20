package com.risk.engine.model;

import lombok.Data;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Data
public class RiskFact {

    private String requestId;

    private String scene;

    private Map<String, Object> data = new HashMap<>();

    private Map<String, Object> variables = new HashMap<>();

    private Set<String> hitRules = new HashSet<>();

    private Set<String> matchedLists = new HashSet<>();

    private Integer score = 0;

    private String decision = "PASS";

    public void addHitRule(String ruleCode) {
        this.hitRules.add(ruleCode);
    }

    public void addMatchedList(String listInfo) {
        this.matchedLists.add(listInfo);
    }

    public void addScore(int score) {
        this.score += score;
    }

    public void setDecision(String decision) {
        this.decision = decision;
    }

    @SuppressWarnings("unchecked")
    public <T> T getDataValue(String key) {
        return (T) data.get(key);
    }

    @SuppressWarnings("unchecked")
    public <T> T getVariableValue(String key) {
        return (T) variables.get(key);
    }
}

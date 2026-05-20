package com.risk.engine.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
public class DecisionResponse {

    private String requestId;

    private String decision;

    private Integer score;

    private List<String> hitRules = new ArrayList<>();

    private Map<String, Object> variables = new HashMap<>();

    private List<String> matchedLists = new ArrayList<>();

    private Long executeTime;

    private Long ruleVersion;

    private String errorMsg;
}

package com.risk.engine.dto;

import lombok.Data;

import java.util.Map;

@Data
public class DecisionRequest {

    private String requestId;

    private String scene;

    private Map<String, Object> data;
}

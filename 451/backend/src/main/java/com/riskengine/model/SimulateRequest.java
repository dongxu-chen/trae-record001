package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.util.Map;

@Data
public class SimulateRequest implements Serializable {
    private String ruleCode;
    private RiskEvent event;
    private Map<String, Object> context;
}

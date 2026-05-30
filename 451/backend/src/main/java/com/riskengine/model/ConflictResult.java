package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;

@Data
public class ConflictResult implements Serializable {
    private String ruleCodeA;
    private String ruleNameA;
    private String ruleCodeB;
    private String ruleNameB;
    private String conflictType;
    private String severity;
    private String description;
    private String suggestion;
}

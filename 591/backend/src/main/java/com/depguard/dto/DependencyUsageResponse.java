package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DependencyUsageResponse {
    private String groupId;
    private String artifactId;
    private String version;
    private String scope;
    private boolean isUsed;
    private boolean isDirectlyUsed;
    private double usageConfidence;
    private List<String> usageEvidence;
    private boolean isSpecialScope;
}

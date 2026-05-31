package com.depguard.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Set;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UsageAnalysisResponse {
    private List<DependencyUsageResponse> dependencyResults;
    private long usedCount;
    private long unusedCount;
    private long unclearCount;
    private List<DependencyUsageResponse> unusedDependencies;
    private Set<String> allImportedPackages;
    private Set<String> allUsedClasses;
}

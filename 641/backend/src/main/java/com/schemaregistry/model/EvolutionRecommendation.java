package com.schemaregistry.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EvolutionRecommendation {
    private String recommendation;
    private String impact;
    private List<String> steps;
    private CompatibilityLevel suggestedCompatibility;
    private List<String> warnings;
    private List<String> detectedRenames;
    private List<String> safeAdditions;
    private List<String> breakingChanges;
}

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
public class EvolutionResult {
    private boolean success;
    private boolean compatible;
    private String subject;
    private Integer oldVersion;
    private Integer newVersion;
    private String oldSchema;
    private String newSchema;
    private List<String> appliedChanges;
    private List<String> warnings;
    private String message;
    private CompatibilityResult compatibilityResult;
}

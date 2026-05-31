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
public class CompatibilityResult {
    private boolean compatible;
    private List<String> errors;
    private List<String> warnings;
    private CompatibilityLevel level;
}

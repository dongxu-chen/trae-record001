package com.schemaregistry.compatibility;

import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.CompatibilityResult;

public interface CompatibilityChecker {
    CompatibilityResult checkCompatibility(String oldSchema, String newSchema, CompatibilityLevel level);
    boolean supports(String schemaType);
}

package com.schemaregistry.dto;

import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.SchemaType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CompatibilityCheckRequest {
    @NotNull(message = "Schema type is required")
    private SchemaType type;

    @NotBlank(message = "Old schema is required")
    private String oldSchema;

    @NotBlank(message = "New schema is required")
    private String newSchema;

    private CompatibilityLevel level;
}

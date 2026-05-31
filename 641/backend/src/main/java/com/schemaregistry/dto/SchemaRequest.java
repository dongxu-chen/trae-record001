package com.schemaregistry.dto;

import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.SchemaType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SchemaRequest {
    @NotBlank(message = "Subject is required")
    private String subject;

    @NotNull(message = "Schema type is required")
    private SchemaType type;

    @NotBlank(message = "Schema content is required")
    private String schema;

    private String description;

    private CompatibilityLevel compatibilityLevel;
}

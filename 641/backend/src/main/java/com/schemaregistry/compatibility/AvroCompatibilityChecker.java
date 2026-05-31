package com.schemaregistry.compatibility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.CompatibilityResult;
import org.apache.avro.Schema;
import org.apache.avro.SchemaValidationException;
import org.apache.avro.SchemaValidator;
import org.apache.avro.SchemaValidatorBuilder;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Component
public class AvroCompatibilityChecker implements CompatibilityChecker {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public CompatibilityResult checkCompatibility(String oldSchemaStr, String newSchemaStr, CompatibilityLevel level) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        try {
            Schema oldSchema = new Schema.Parser().parse(oldSchemaStr);
            Schema newSchema = new Schema.Parser().parse(newSchemaStr);

            boolean compatible = true;

            switch (level) {
                case FORWARD:
                case FORWARD_TRANSITIVE:
                    compatible = checkForwardCompatibility(oldSchema, newSchema, errors, warnings);
                    break;
                case BACKWARD:
                case BACKWARD_TRANSITIVE:
                    compatible = checkBackwardCompatibility(oldSchema, newSchema, errors, warnings);
                    break;
                case FULL:
                case FULL_TRANSITIVE:
                    boolean backwardOk = checkBackwardCompatibility(oldSchema, newSchema, errors, warnings);
                    boolean forwardOk = checkForwardCompatibility(oldSchema, newSchema, errors, warnings);
                    compatible = backwardOk && forwardOk;
                    break;
                case NONE:
                    compatible = true;
                    warnings.add("Compatibility check skipped (NONE level)");
                    break;
            }

            return CompatibilityResult.builder()
                    .compatible(compatible)
                    .errors(errors)
                    .warnings(warnings)
                    .level(level)
                    .build();

        } catch (Exception e) {
            errors.add("Schema parsing error: " + e.getMessage());
            return CompatibilityResult.builder()
                    .compatible(false)
                    .errors(errors)
                    .warnings(warnings)
                    .level(level)
                    .build();
        }
    }

    private boolean checkBackwardCompatibility(Schema oldSchema, Schema newSchema, List<String> errors, List<String> warnings) {
        SchemaValidator validator = new SchemaValidatorBuilder()
                .canReadStrategy()
                .validateLatest();
        try {
            validator.validate(newSchema, Collections.singletonList(oldSchema));
            checkNewFieldsWithDefaults(oldSchema, newSchema, errors, warnings);
            return true;
        } catch (SchemaValidationException e) {
            errors.addAll(e.getErrorMessages());
            return false;
        }
    }

    private boolean checkForwardCompatibility(Schema oldSchema, Schema newSchema, List<String> errors, List<String> warnings) {
        SchemaValidator validator = new SchemaValidatorBuilder()
                .canBeReadStrategy()
                .validateLatest();
        try {
            validator.validate(oldSchema, Collections.singletonList(newSchema));
            checkNewFieldsWithDefaults(oldSchema, newSchema, errors, warnings);
            return true;
        } catch (SchemaValidationException e) {
            errors.addAll(e.getErrorMessages());
            return false;
        }
    }

    private void checkNewFieldsWithDefaults(Schema oldSchema, Schema newSchema, List<String> errors, List<String> warnings) {
        if (oldSchema.getType() == Schema.Type.RECORD && newSchema.getType() == Schema.Type.RECORD) {
            java.util.Map<String, Schema.Field> oldFields = new java.util.HashMap<>();
            for (Schema.Field field : oldSchema.getFields()) {
                oldFields.put(field.name(), field);
            }

            for (Schema.Field field : newSchema.getFields()) {
                if (!oldFields.containsKey(field.name())) {
                    Object defaultValue = field.defaultVal();
                    if (defaultValue != null && !defaultValue.toString().equals("null")) {
                        warnings.add("New field '" + field.name() + "' added with default value: " + defaultValue + " (compatible)");
                    } else if (field.schema().getType() == Schema.Type.UNION) {
                        boolean hasNullType = field.schema().getTypes().stream()
                                .anyMatch(t -> t.getType() == Schema.Type.NULL);
                        if (hasNullType) {
                            warnings.add("New nullable field '" + field.name() + "' added (compatible)");
                        }
                    }
                }
            }
        }
    }

    @Override
    public boolean supports(String schemaType) {
        return "AVRO".equalsIgnoreCase(schemaType);
    }
}

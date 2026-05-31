package com.schemaregistry.compatibility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.CompatibilityResult;
import org.everit.json.schema.Schema;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

@Component
public class JsonSchemaCompatibilityChecker implements CompatibilityChecker {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public CompatibilityResult checkCompatibility(String oldSchemaStr, String newSchemaStr, CompatibilityLevel level) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        try {
            JsonNode oldSchema = objectMapper.readTree(oldSchemaStr);
            JsonNode newSchema = objectMapper.readTree(newSchemaStr);

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

    private boolean checkBackwardCompatibility(JsonNode oldSchema, JsonNode newSchema, List<String> errors, List<String> warnings) {
        JsonNode oldProperties = oldSchema.path("properties");
        JsonNode newProperties = newSchema.path("properties");
        JsonNode oldRequired = oldSchema.path("required");
        JsonNode newRequired = newSchema.path("required");

        if (oldProperties.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = oldProperties.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String fieldName = field.getKey();

                if (!newProperties.has(fieldName)) {
                    if (isRequired(oldRequired, fieldName)) {
                        errors.add("Required field removed: " + fieldName);
                        return false;
                    }
                } else {
                    JsonNode oldType = field.getValue().path("type");
                    JsonNode newType = newProperties.path(fieldName).path("type");
                    if (!oldType.equals(newType) && !oldType.isArray() && !newType.isArray()) {
                        errors.add("Type changed for field '" + fieldName + "': " + oldType + " -> " + newType);
                        return false;
                    }
                }
            }
        }

        if (newProperties.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> newFields = newProperties.fields();
            while (newFields.hasNext()) {
                Map.Entry<String, JsonNode> field = newFields.next();
                String fieldName = field.getKey();
                if (!oldProperties.has(fieldName)) {
                    JsonNode newField = field.getValue();
                    boolean hasDefault = newField.has("default");
                    boolean isRequired = isRequired(newRequired, fieldName);

                    if (isRequired && !hasDefault) {
                        errors.add("New required field '" + fieldName + "' added without default value");
                        return false;
                    } else if (hasDefault) {
                        warnings.add("New field '" + fieldName + "' added with default value: " + newField.path("default") + " (compatible)");
                    } else {
                        warnings.add("New optional field '" + fieldName + "' added (compatible)");
                    }
                }
            }
        }

        if (newRequired.isArray()) {
            for (JsonNode req : newRequired) {
                String fieldName = req.asText();
                if (!oldProperties.has(fieldName) && newProperties.has(fieldName)) {
                    JsonNode newField = newProperties.path(fieldName);
                    if (!newField.has("default")) {
                        errors.add("New required field without default: " + fieldName);
                        return false;
                    }
                }
            }
        }

        return true;
    }

    private boolean checkForwardCompatibility(JsonNode oldSchema, JsonNode newSchema, List<String> errors, List<String> warnings) {
        JsonNode oldProperties = oldSchema.path("properties");
        JsonNode newProperties = newSchema.path("properties");
        JsonNode newRequired = newSchema.path("required");
        JsonNode oldRequired = oldSchema.path("required");

        if (newProperties.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = newProperties.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String fieldName = field.getKey();

                if (!oldProperties.has(fieldName)) {
                    boolean isRequired = isRequired(newRequired, fieldName);
                    boolean hasDefault = field.getValue().has("default");
                    if (isRequired && !hasDefault) {
                        errors.add("New required field '" + fieldName + "' added without default value (breaks forward compatibility)");
                        return false;
                    } else if (hasDefault) {
                        warnings.add("New field '" + fieldName + "' added with default value: " + field.getValue().path("default") + " (compatible)");
                    }
                }
            }
        }

        if (oldProperties.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> oldFields = oldProperties.fields();
            while (oldFields.hasNext()) {
                Map.Entry<String, JsonNode> field = oldFields.next();
                String fieldName = field.getKey();
                if (!newProperties.has(fieldName) && isRequired(oldRequired, fieldName)) {
                    warnings.add("Required field '" + fieldName + "' removed (consumers must handle missing field)");
                }
            }
        }

        return true;
    }

    private boolean isRequired(JsonNode requiredNode, String fieldName) {
        if (requiredNode.isArray()) {
            for (JsonNode node : requiredNode) {
                if (fieldName.equals(node.asText())) {
                    return true;
                }
            }
        }
        return false;
    }

    @Override
    public boolean supports(String schemaType) {
        return "JSON_SCHEMA".equalsIgnoreCase(schemaType);
    }
}

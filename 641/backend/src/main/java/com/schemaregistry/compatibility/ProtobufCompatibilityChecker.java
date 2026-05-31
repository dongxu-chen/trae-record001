package com.schemaregistry.compatibility;

import com.schemaregistry.model.CompatibilityLevel;
import com.schemaregistry.model.CompatibilityResult;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class ProtobufCompatibilityChecker implements CompatibilityChecker {

    @Override
    public CompatibilityResult checkCompatibility(String oldSchemaStr, String newSchemaStr, CompatibilityLevel level) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        try {
            boolean compatible = true;

            switch (level) {
                case FORWARD:
                case FORWARD_TRANSITIVE:
                    compatible = checkForwardCompatibility(oldSchemaStr, newSchemaStr, errors, warnings);
                    break;
                case BACKWARD:
                case BACKWARD_TRANSITIVE:
                    compatible = checkBackwardCompatibility(oldSchemaStr, newSchemaStr, errors, warnings);
                    break;
                case FULL:
                case FULL_TRANSITIVE:
                    boolean backwardOk = checkBackwardCompatibility(oldSchemaStr, newSchemaStr, errors, warnings);
                    boolean forwardOk = checkForwardCompatibility(oldSchemaStr, newSchemaStr, errors, warnings);
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

    private boolean checkBackwardCompatibility(String oldSchema, String newSchema, List<String> errors, List<String> warnings) {
        Pattern fieldPattern = Pattern.compile("(required|optional|repeated)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*(\\d+)");

        java.util.Map<Integer, FieldInfo> oldFields = extractFieldInfo(oldSchema, fieldPattern);
        java.util.Map<Integer, FieldInfo> newFields = extractFieldInfo(newSchema, fieldPattern);

        for (java.util.Map.Entry<Integer, FieldInfo> entry : oldFields.entrySet()) {
            int tag = entry.getKey();
            FieldInfo oldField = entry.getValue();

            if (newFields.containsKey(tag)) {
                FieldInfo newField = newFields.get(tag);
                if (!oldField.definition.equals(newField.definition)) {
                    errors.add("Field type changed for tag " + tag + ": " + oldField.definition + " -> " + newField.definition);
                    return false;
                }
            } else {
                errors.add("Field with tag " + tag + " was removed");
                return false;
            }
        }

        for (java.util.Map.Entry<Integer, FieldInfo> entry : newFields.entrySet()) {
            int tag = entry.getKey();
            FieldInfo newField = entry.getValue();
            if (!oldFields.containsKey(tag)) {
                if ("optional".equals(newField.rule)) {
                    warnings.add("New optional field '" + newField.name + "' (tag " + tag + ") added (compatible)");
                } else if ("repeated".equals(newField.rule)) {
                    warnings.add("New repeated field '" + newField.name + "' (tag " + tag + ") added (compatible)");
                }
            }
        }

        return true;
    }

    private boolean checkForwardCompatibility(String oldSchema, String newSchema, List<String> errors, List<String> warnings) {
        Pattern fieldPattern = Pattern.compile("(required)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*(\\d+)");
        Pattern allFieldPattern = Pattern.compile("(required|optional|repeated)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*(\\d+)");

        java.util.Map<Integer, FieldInfo> oldRequiredFields = extractFieldInfo(oldSchema, fieldPattern);
        java.util.Map<Integer, FieldInfo> newFields = extractFieldInfo(newSchema, allFieldPattern);

        for (java.util.Map.Entry<Integer, FieldInfo> entry : oldRequiredFields.entrySet()) {
            int tag = entry.getKey();
            if (!newFields.containsKey(tag)) {
                errors.add("Required field with tag " + tag + " is missing in new schema");
                return false;
            }
        }

        for (java.util.Map.Entry<Integer, FieldInfo> entry : newFields.entrySet()) {
            int tag = entry.getKey();
            FieldInfo newField = entry.getValue();
            if (!oldRequiredFields.containsKey(tag) && "required".equals(newField.rule)) {
                warnings.add("New required field '" + newField.name + "' (tag " + tag + ") added - old consumers may fail");
            }
        }

        return true;
    }

    private static class FieldInfo {
        String rule;
        String type;
        String name;
        String definition;

        FieldInfo(String rule, String type, String name) {
            this.rule = rule;
            this.type = type;
            this.name = name;
            this.definition = rule + " " + type + " " + name;
        }
    }

    private java.util.Map<Integer, FieldInfo> extractFieldInfo(String schema, Pattern pattern) {
        java.util.Map<Integer, FieldInfo> fields = new java.util.HashMap<>();
        java.util.regex.Matcher matcher = pattern.matcher(schema);

        while (matcher.find()) {
            String rule = matcher.group(1);
            String type = matcher.group(2);
            String name = matcher.group(3);
            int tag = Integer.parseInt(matcher.group(4));
            fields.put(tag, new FieldInfo(rule, type, name));
        }

        return fields;
    }

    @Override
    public boolean supports(String schemaType) {
        return "PROTOBUF".equalsIgnoreCase(schemaType);
    }
}

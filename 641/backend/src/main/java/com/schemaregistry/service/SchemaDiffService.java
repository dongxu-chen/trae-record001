package com.schemaregistry.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.schemaregistry.model.DiffEntry;
import com.schemaregistry.model.SchemaDiff;
import com.schemaregistry.model.SchemaType;
import com.schemaregistry.model.StructuredDiffNode;
import com.schemaregistry.util.StringSimilarity;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class SchemaDiffService {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private static final double RENAME_THRESHOLD = 0.75;

    public SchemaDiff compareSchemas(String oldSchema, String newSchema, SchemaType type, String oldVersion, String newVersion) {
        List<DiffEntry> additions = new ArrayList<>();
        List<DiffEntry> deletions = new ArrayList<>();
        List<DiffEntry> modifications = new ArrayList<>();
        List<DiffEntry> renames = new ArrayList<>();
        List<StructuredDiffNode> structuredDiff = new ArrayList<>();

        try {
            switch (type) {
                case AVRO:
                case JSON_SCHEMA:
                    compareJsonSchemas(oldSchema, newSchema, additions, deletions, modifications, renames, structuredDiff);
                    break;
                case PROTOBUF:
                    compareProtobufSchemas(oldSchema, newSchema, additions, deletions, modifications, renames, structuredDiff);
                    break;
            }
        } catch (Exception e) {
            modifications.add(DiffEntry.builder()
                    .field("parse_error")
                    .description("Failed to parse schemas: " + e.getMessage())
                    .build());
        }

        return SchemaDiff.builder()
                .oldVersion(oldVersion)
                .newVersion(newVersion)
                .additions(additions)
                .deletions(deletions)
                .modifications(modifications)
                .renames(renames)
                .structuredDiff(structuredDiff)
                .build();
    }

    private void compareJsonSchemas(String oldSchemaStr, String newSchemaStr,
                                    List<DiffEntry> additions, List<DiffEntry> deletions,
                                    List<DiffEntry> modifications, List<DiffEntry> renames,
                                    List<StructuredDiffNode> structuredDiff) throws Exception {
        JsonNode oldSchema = objectMapper.readTree(oldSchemaStr);
        JsonNode newSchema = objectMapper.readTree(newSchemaStr);

        JsonNode oldProperties = oldSchema.path("fields");
        JsonNode newProperties = newSchema.path("fields");

        if (!oldProperties.isArray()) {
            oldProperties = oldSchema.path("properties");
        }
        if (!newProperties.isArray()) {
            newProperties = newSchema.path("properties");
        }

        Map<String, JsonNode> oldFieldsMap = extractJsonFields(oldProperties);
        Map<String, JsonNode> newFieldsMap = extractJsonFields(newProperties);

        Set<String> allFields = new TreeSet<>();
        allFields.addAll(oldFieldsMap.keySet());
        allFields.addAll(newFieldsMap.keySet());

        Map<String, String> detectedRenames = detectFieldRenames(oldFieldsMap.keySet(), newFieldsMap.keySet());

        for (String fieldName : allFields) {
            StructuredDiffNode node = new StructuredDiffNode();
            node.setFieldName(fieldName);
            node.setLevel(1);

            boolean inOld = oldFieldsMap.containsKey(fieldName);
            boolean inNew = newFieldsMap.containsKey(fieldName);
            boolean isRenameTarget = detectedRenames.containsValue(fieldName);
            boolean isRenameSource = detectedRenames.containsKey(fieldName);

            if (inOld && inNew) {
                JsonNode oldField = oldFieldsMap.get(fieldName);
                JsonNode newField = newFieldsMap.get(fieldName);
                compareFieldDetails(node, oldField, newField, fieldName, "", modifications, additions, deletions);
            } else if (inOld && !inNew) {
                if (isRenameSource) {
                    String newName = detectedRenames.get(fieldName);
                    double confidence = StringSimilarity.calculateCombinedSimilarity(fieldName, newName);
                    node.setChangeType(StructuredDiffNode.ChangeType.RENAMED);
                    node.setRenameFrom(fieldName);
                    node.setRenameTo(newName);
                    node.setRenameConfidence(confidence);
                    node.setOldType(getFieldType(oldFieldsMap.get(fieldName)));

                    renames.add(DiffEntry.builder()
                            .field(fieldName + " -> " + newName)
                            .oldFieldName(fieldName)
                            .newFieldName(newName)
                            .renameConfidence(confidence)
                            .type(DiffEntry.DiffType.FIELD_RENAMED)
                            .description(String.format("Field renamed (confidence: %.1f%%)", confidence * 100))
                            .build());
                } else {
                    node.setChangeType(StructuredDiffNode.ChangeType.REMOVED);
                    node.setOldType(getFieldType(oldFieldsMap.get(fieldName)));
                    node.setOldRequired(isFieldRequired(oldSchema, fieldName));

                    deletions.add(DiffEntry.builder()
                            .path(fieldName)
                            .field(fieldName)
                            .oldValue(oldFieldsMap.get(fieldName).toString())
                            .type(DiffEntry.DiffType.FIELD_REMOVED)
                            .description("Field removed")
                            .build());
                }
            } else if (!inOld && inNew) {
                if (!isRenameTarget) {
                    node.setChangeType(StructuredDiffNode.ChangeType.ADDED);
                    JsonNode newField = newFieldsMap.get(fieldName);
                    node.setNewType(getFieldType(newField));
                    node.setNewRequired(isFieldRequired(newSchema, fieldName));
                    boolean hasDefault = newField.has("default");
                    node.setHasDefault(hasDefault);

                    additions.add(DiffEntry.builder()
                            .path(fieldName)
                            .field(fieldName)
                            .newValue(newField.toString())
                            .hasDefault(hasDefault)
                            .type(DiffEntry.DiffType.FIELD_ADDED)
                            .description(hasDefault ? "Field added with default value (compatible)" : "Field added")
                            .build());
                } else {
                    continue;
                }
            }

            if (node.getChangeType() != null || node.getChildren() != null && !node.getChildren().isEmpty()) {
                structuredDiff.add(node);
            }
        }
    }

    private Map<String, JsonNode> extractJsonFields(JsonNode propertiesNode) {
        Map<String, JsonNode> fields = new LinkedHashMap<>();

        if (propertiesNode.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> iterator = propertiesNode.fields();
            while (iterator.hasNext()) {
                Map.Entry<String, JsonNode> entry = iterator.next();
                fields.put(entry.getKey(), entry.getValue());
            }
        } else if (propertiesNode.isArray()) {
            for (JsonNode fieldNode : propertiesNode) {
                if (fieldNode.has("name")) {
                    String name = fieldNode.get("name").asText();
                    fields.put(name, fieldNode);
                }
            }
        }

        return fields;
    }

    private void compareFieldDetails(StructuredDiffNode node, JsonNode oldField, JsonNode newField,
                                     String fieldName, String path, List<DiffEntry> modifications,
                                     List<DiffEntry> additions, List<DiffEntry> deletions) {
        String fullPath = path.isEmpty() ? fieldName : path + "." + fieldName;
        boolean modified = false;

        String oldType = getFieldType(oldField);
        String newType = getFieldType(newField);
        node.setOldType(oldType);
        node.setNewType(newType);

        if (!oldType.equals(newType)) {
            modified = true;
            modifications.add(DiffEntry.builder()
                    .path(fullPath)
                    .field(fieldName)
                    .oldValue(oldType)
                    .newValue(newType)
                    .type(DiffEntry.DiffType.TYPE_CHANGED)
                    .description("Type changed: " + oldType + " -> " + newType)
                    .build());
        }

        JsonNode oldDefault = oldField.path("default");
        JsonNode newDefault = newField.path("default");
        if (!oldDefault.isMissingNode() || !newDefault.isMissingNode()) {
            String oldDefaultStr = oldDefault.isMissingNode() ? "none" : oldDefault.toString();
            String newDefaultStr = newDefault.isMissingNode() ? "none" : newDefault.toString();
            node.setOldDefault(oldDefault.isMissingNode() ? null : oldDefault.asText());
            node.setNewDefault(newDefault.isMissingNode() ? null : newDefault.asText());

            if (!oldDefaultStr.equals(newDefaultStr)) {
                modified = true;
                modifications.add(DiffEntry.builder()
                        .path(fullPath)
                        .field(fieldName)
                        .oldValue(oldDefaultStr)
                        .newValue(newDefaultStr)
                        .type(DiffEntry.DiffType.DEFAULT_CHANGED)
                        .description("Default value changed")
                        .build());
            }
        }

        if (modified) {
            node.setChangeType(StructuredDiffNode.ChangeType.MODIFIED);
        } else {
            node.setChangeType(StructuredDiffNode.ChangeType.UNCHANGED);
        }
    }

    private String getFieldType(JsonNode fieldNode) {
        if (fieldNode.has("type")) {
            JsonNode typeNode = fieldNode.get("type");
            if (typeNode.isTextual()) {
                return typeNode.asText();
            } else if (typeNode.isArray()) {
                return typeNode.toString();
            }
        }
        return fieldNode.path("type").asText("object");
    }

    private boolean isFieldRequired(JsonNode schema, String fieldName) {
        JsonNode requiredNode = schema.path("required");
        if (requiredNode.isArray()) {
            for (JsonNode req : requiredNode) {
                if (fieldName.equals(req.asText())) {
                    return true;
                }
            }
        }
        return false;
    }

    private Map<String, String> detectFieldRenames(Set<String> oldFields, Set<String> newFields) {
        Map<String, String> renames = new HashMap<>();
        Set<String> deletedFields = oldFields.stream()
                .filter(f -> !newFields.contains(f))
                .collect(Collectors.toSet());
        Set<String> addedFields = newFields.stream()
                .filter(f -> !oldFields.contains(f))
                .collect(Collectors.toSet());

        Set<String> matchedNew = new HashSet<>();

        for (String oldField : deletedFields) {
            double bestScore = 0;
            String bestMatch = null;

            for (String newField : addedFields) {
                if (matchedNew.contains(newField)) continue;

                double similarity = StringSimilarity.calculateCombinedSimilarity(oldField, newField);
                if (similarity > bestScore && StringSimilarity.isLikelyRename(oldField, newField, RENAME_THRESHOLD)) {
                    bestScore = similarity;
                    bestMatch = newField;
                }
            }

            if (bestMatch != null) {
                renames.put(oldField, bestMatch);
                matchedNew.add(bestMatch);
            }
        }

        return renames;
    }

    private void compareProtobufSchemas(String oldSchema, String newSchema,
                                        List<DiffEntry> additions, List<DiffEntry> deletions,
                                        List<DiffEntry> modifications, List<DiffEntry> renames,
                                        List<StructuredDiffNode> structuredDiff) {
        java.util.regex.Pattern fieldPattern = java.util.regex.Pattern.compile("(required|optional|repeated)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*(\\d+)");

        Map<Integer, ProtobufField> oldFields = extractProtobufFields(oldSchema, fieldPattern);
        Map<Integer, ProtobufField> newFields = extractProtobufFields(newSchema, fieldPattern);

        Map<String, String> detectedRenames = detectProtobufRenames(oldFields, newFields);
        Set<Integer> allTags = new TreeSet<>();
        allTags.addAll(oldFields.keySet());
        allTags.addAll(newFields.keySet());

        for (Integer tag : allTags) {
            StructuredDiffNode node = new StructuredDiffNode();
            node.setLevel(1);

            boolean inOld = oldFields.containsKey(tag);
            boolean inNew = newFields.containsKey(tag);

            if (inOld && inNew) {
                ProtobufField oldField = oldFields.get(tag);
                ProtobufField newField = newFields.get(tag);
                node.setFieldName(oldField.name);
                node.setOldType(oldField.type);
                node.setNewType(newField.type);
                node.setOldRequired("required".equals(oldField.rule));
                node.setNewRequired("required".equals(newField.rule));

                if (!oldField.type.equals(newField.type) || !oldField.rule.equals(newField.rule)) {
                    node.setChangeType(StructuredDiffNode.ChangeType.MODIFIED);
                    modifications.add(DiffEntry.builder()
                            .path("tag." + tag)
                            .field(oldField.name)
                            .oldValue(oldField.rule + " " + oldField.type)
                            .newValue(newField.rule + " " + newField.type)
                            .type(DiffEntry.DiffType.TYPE_CHANGED)
                            .description("Field definition changed for tag " + tag)
                            .build());
                } else {
                    node.setChangeType(StructuredDiffNode.ChangeType.UNCHANGED);
                }
            } else if (inOld && !inNew) {
                ProtobufField oldField = oldFields.get(tag);
                node.setFieldName(oldField.name);
                node.setOldType(oldField.type);
                node.setOldRequired("required".equals(oldField.rule));

                String newName = detectedRenames.get(oldField.name);
                if (newName != null) {
                    double confidence = StringSimilarity.calculateCombinedSimilarity(oldField.name, newName);
                    node.setChangeType(StructuredDiffNode.ChangeType.RENAMED);
                    node.setRenameFrom(oldField.name);
                    node.setRenameTo(newName);
                    node.setRenameConfidence(confidence);

                    renames.add(DiffEntry.builder()
                            .field(oldField.name + " -> " + newName)
                            .oldFieldName(oldField.name)
                            .newFieldName(newName)
                            .renameConfidence(confidence)
                            .type(DiffEntry.DiffType.FIELD_RENAMED)
                            .description(String.format("Field renamed (confidence: %.1f%%)", confidence * 100))
                            .build());
                } else {
                    node.setChangeType(StructuredDiffNode.ChangeType.REMOVED);
                    deletions.add(DiffEntry.builder()
                            .path("tag." + tag)
                            .field(oldField.name)
                            .oldValue(oldField.rule + " " + oldField.type)
                            .type(DiffEntry.DiffType.FIELD_REMOVED)
                            .description("Field removed (tag " + tag + ")")
                            .build());
                }
            } else {
                ProtobufField newField = newFields.get(tag);
                boolean isRenameTarget = detectedRenames.containsValue(newField.name);

                if (!isRenameTarget) {
                    node.setFieldName(newField.name);
                    node.setChangeType(StructuredDiffNode.ChangeType.ADDED);
                    node.setNewType(newField.type);
                    node.setNewRequired("required".equals(newField.rule));

                    additions.add(DiffEntry.builder()
                            .path("tag." + tag)
                            .field(newField.name)
                            .newValue(newField.rule + " " + newField.type)
                            .type(DiffEntry.DiffType.FIELD_ADDED)
                            .description("Field added (tag " + tag + ")")
                            .build());
                } else {
                    continue;
                }
            }

            if (node.getChangeType() != null) {
                structuredDiff.add(node);
            }
        }
    }

    private Map<String, String> detectProtobufRenames(Map<Integer, ProtobufField> oldFields, Map<Integer, ProtobufField> newFields) {
        Map<String, String> renames = new HashMap<>();
        Set<String> oldNames = oldFields.values().stream().map(f -> f.name).collect(Collectors.toSet());
        Set<String> newNames = newFields.values().stream().map(f -> f.name).collect(Collectors.toSet());

        Set<String> deletedNames = oldNames.stream()
                .filter(n -> !newNames.contains(n))
                .collect(Collectors.toSet());
        Set<String> addedNames = newNames.stream()
                .filter(n -> !oldNames.contains(n))
                .collect(Collectors.toSet());

        Set<String> matchedNew = new HashSet<>();

        for (String oldName : deletedNames) {
            double bestScore = 0;
            String bestMatch = null;

            for (String newName : addedNames) {
                if (matchedNew.contains(newName)) continue;

                double similarity = StringSimilarity.calculateCombinedSimilarity(oldName, newName);
                if (similarity > bestScore && StringSimilarity.isLikelyRename(oldName, newName, RENAME_THRESHOLD)) {
                    bestScore = similarity;
                    bestMatch = newName;
                }
            }

            if (bestMatch != null) {
                renames.put(oldName, bestMatch);
                matchedNew.add(bestMatch);
            }
        }

        return renames;
    }

    private Map<Integer, ProtobufField> extractProtobufFields(String schema, java.util.regex.Pattern pattern) {
        Map<Integer, ProtobufField> fields = new TreeMap<>();
        java.util.regex.Matcher matcher = pattern.matcher(schema);

        while (matcher.find()) {
            int tag = Integer.parseInt(matcher.group(4));
            fields.put(tag, new ProtobufField(matcher.group(1), matcher.group(2), matcher.group(3)));
        }

        return fields;
    }

    private static class ProtobufField {
        String rule;
        String type;
        String name;

        ProtobufField(String rule, String type, String name) {
            this.rule = rule;
            this.type = type;
            this.name = name;
        }
    }
}

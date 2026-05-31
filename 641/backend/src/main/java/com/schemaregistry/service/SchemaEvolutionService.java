package com.schemaregistry.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.schemaregistry.model.*;
import com.schemaregistry.repository.SchemaRepository;
import com.schemaregistry.repository.SchemaVersionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
public class SchemaEvolutionService {

    private final SchemaRepository schemaRepository;
    private final SchemaVersionRepository versionRepository;
    private final SchemaService schemaService;
    private final AuditService auditService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    public SchemaEvolutionService(SchemaRepository schemaRepository,
                                  SchemaVersionRepository versionRepository,
                                  SchemaService schemaService,
                                  AuditService auditService) {
        this.schemaRepository = schemaRepository;
        this.versionRepository = versionRepository;
        this.schemaService = schemaService;
        this.auditService = auditService;
    }

    @Transactional
    public EvolutionResult autoEvolveSchema(String subject, String proposedSchema, String username) {
        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));

        SchemaVersion latestVersion = versionRepository.findMaxVersionBySchemaId(schema.getId())
                .flatMap(maxVer -> versionRepository.findBySubjectAndVersion(subject, maxVer))
                .orElseThrow(() -> new RuntimeException("No version found for schema: " + subject));

        String currentSchema = latestVersion.getSchemaText();
        List<String> appliedChanges = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        CompatibilityResult compatibilityResult = schemaService.checkCompatibility(
                schema.getType(),
                currentSchema,
                proposedSchema,
                schema.getCompatibilityLevel()
        );

        if (!compatibilityResult.isCompatible()) {
            String evolvedSchema = evolveSchema(currentSchema, proposedSchema, schema.getType(), appliedChanges, warnings);

            CompatibilityResult evolvedCompatibility = schemaService.checkCompatibility(
                    schema.getType(),
                    currentSchema,
                    evolvedSchema,
                    schema.getCompatibilityLevel()
            );

            if (!evolvedCompatibility.isCompatible()) {
                return EvolutionResult.builder()
                        .success(false)
                        .compatible(false)
                        .subject(subject)
                        .oldVersion(latestVersion.getVersion())
                        .message("Cannot auto-evolve schema. Incompatible changes detected: " + evolvedCompatibility.getErrors())
                        .warnings(warnings)
                        .compatibilityResult(evolvedCompatibility)
                        .build();
            }

            Integer newVersion = createNewVersion(schema, latestVersion, evolvedSchema, appliedChanges, username);

            return EvolutionResult.builder()
                    .success(true)
                    .compatible(true)
                    .subject(subject)
                    .oldVersion(latestVersion.getVersion())
                    .newVersion(newVersion)
                    .oldSchema(currentSchema)
                    .newSchema(evolvedSchema)
                    .appliedChanges(appliedChanges)
                    .warnings(warnings)
                    .message("Schema auto-evolved successfully. Applied " + appliedChanges.size() + " changes.")
                    .compatibilityResult(evolvedCompatibility)
                    .build();
        }

        Integer newVersion = createNewVersion(schema, latestVersion, proposedSchema,
                Collections.singletonList("Schema submitted is already compatible, added as new version"), username);

        return EvolutionResult.builder()
                .success(true)
                .compatible(true)
                .subject(subject)
                .oldVersion(latestVersion.getVersion())
                .newVersion(newVersion)
                .oldSchema(currentSchema)
                .newSchema(proposedSchema)
                .appliedChanges(appliedChanges)
                .warnings(warnings)
                .message("Schema is compatible, added as new version.")
                .compatibilityResult(compatibilityResult)
                .build();
    }

    private String evolveSchema(String currentSchema, String proposedSchema, SchemaType type,
                                List<String> appliedChanges, List<String> warnings) {
        try {
            switch (type) {
                case AVRO:
                    return evolveAvroSchema(currentSchema, proposedSchema, appliedChanges, warnings);
                case JSON_SCHEMA:
                    return evolveJsonSchema(currentSchema, proposedSchema, appliedChanges, warnings);
                case PROTOBUF:
                    return evolveProtobufSchema(currentSchema, proposedSchema, appliedChanges, warnings);
                default:
                    throw new RuntimeException("Unsupported schema type: " + type);
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to evolve schema: " + e.getMessage(), e);
        }
    }

    private String evolveAvroSchema(String currentSchemaStr, String proposedSchemaStr,
                                    List<String> appliedChanges, List<String> warnings) throws Exception {
        ObjectNode currentSchema = (ObjectNode) objectMapper.readTree(currentSchemaStr);
        ObjectNode proposedSchema = (ObjectNode) objectMapper.readTree(proposedSchemaStr);

        ArrayNode currentFields = (ArrayNode) currentSchema.get("fields");
        ArrayNode proposedFields = (ArrayNode) proposedSchema.get("fields");

        Map<String, JsonNode> currentFieldMap = new HashMap<>();
        for (JsonNode field : currentFields) {
            currentFieldMap.put(field.get("name").asText(), field);
        }

        ArrayNode newFields = objectMapper.createArrayNode();

        for (JsonNode currentField : currentFields) {
            newFields.add(currentField);
        }

        for (JsonNode proposedField : proposedFields) {
            String fieldName = proposedField.get("name").asText();
            if (!currentFieldMap.containsKey(fieldName)) {
                ObjectNode newField = (ObjectNode) proposedField;
                if (!newField.has("default")) {
                    if (newField.has("type") && newField.get("type").isArray()) {
                        ArrayNode typeArray = (ArrayNode) newField.get("type");
                        boolean hasNull = false;
                        for (JsonNode type : typeArray) {
                            if ("null".equals(type.asText())) {
                                hasNull = true;
                                break;
                            }
                        }
                        if (!hasNull) {
                            ArrayNode newTypeArray = objectMapper.createArrayNode();
                            newTypeArray.add("null");
                            for (JsonNode type : typeArray) {
                                newTypeArray.add(type);
                            }
                            newField.set("type", newTypeArray);
                            newField.putNull("default");
                            appliedChanges.add("Added nullable union type and null default for new field: " + fieldName);
                        }
                    } else {
                        ArrayNode newTypeArray = objectMapper.createArrayNode();
                        newTypeArray.add("null");
                        newTypeArray.add(newField.get("type"));
                        newField.set("type", newTypeArray);
                        newField.putNull("default");
                        appliedChanges.add("Converted new field '" + fieldName + "' to nullable type with null default");
                    }
                } else {
                    appliedChanges.add("Added new field: " + fieldName + " (has default value)");
                }
                newFields.add(newField);
            } else {
                JsonNode currentField = currentFieldMap.get(fieldName);
                JsonNode currentType = currentField.get("type");
                JsonNode newType = proposedField.get("type");

                if (!currentType.equals(newType)) {
                    warnings.add("Field '" + fieldName + "' type change detected. Kept original type to maintain compatibility.");
                }
            }
        }

        currentSchema.set("fields", newFields);
        return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(currentSchema);
    }

    private String evolveJsonSchema(String currentSchemaStr, String proposedSchemaStr,
                                    List<String> appliedChanges, List<String> warnings) throws Exception {
        ObjectNode currentSchema = (ObjectNode) objectMapper.readTree(currentSchemaStr);
        ObjectNode proposedSchema = (ObjectNode) objectMapper.readTree(proposedSchemaStr);

        ObjectNode currentProps = (ObjectNode) currentSchema.path("properties");
        ObjectNode proposedProps = (ObjectNode) proposedSchema.path("properties");
        ArrayNode currentRequired = currentSchema.has("required") ? (ArrayNode) currentSchema.get("required") : null;

        ObjectNode newProps = objectMapper.createObjectNode();

        if (currentProps != null) {
            Iterator<Map.Entry<String, JsonNode>> fields = currentProps.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                newProps.set(field.getKey(), field.getValue());
            }
        }

        if (proposedProps != null) {
            Iterator<Map.Entry<String, JsonNode>> fields = proposedProps.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String fieldName = field.getKey();
                if (currentProps == null || !currentProps.has(fieldName)) {
                    ObjectNode newField = (ObjectNode) field.getValue();
                    if (!newField.has("default")) {
                        newField.put("default", getDefaultForType(newField.path("type").asText()));
                        appliedChanges.add("Added default value for new field: " + fieldName);
                    } else {
                        appliedChanges.add("Added new field: " + fieldName + " (has default value)");
                    }
                    newProps.set(fieldName, newField);
                } else {
                    JsonNode currentField = currentProps.get(fieldName);
                    JsonNode currentType = currentField.path("type");
                    JsonNode newType = field.getValue().path("type");
                    if (!currentType.equals(newType)) {
                        warnings.add("Field '" + fieldName + "' type change detected. Kept original type to maintain compatibility.");
                        newProps.set(fieldName, currentField);
                    }
                }
            }
        }

        currentSchema.set("properties", newProps);

        if (currentRequired != null) {
            ArrayNode newRequired = objectMapper.createArrayNode();
            for (JsonNode req : currentRequired) {
                newRequired.add(req);
            }
            currentSchema.set("required", newRequired);
        }

        return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(currentSchema);
    }

    private String getDefaultForType(String type) {
        switch (type) {
            case "string": return "";
            case "integer":
            case "number": return "0";
            case "boolean": return "false";
            case "array": return "[]";
            case "object": return "{}";
            default: return "";
        }
    }

    private String evolveProtobufSchema(String currentSchema, String proposedSchema,
                                        List<String> appliedChanges, List<String> warnings) {
        Set<Integer> currentTags = extractProtobufTags(currentSchema);
        Set<Integer> proposedTags = extractProtobufTags(proposedSchema);

        int nextTag = Collections.max(currentTags) + 1;

        StringBuilder evolvedSchema = new StringBuilder(currentSchema);

        java.util.regex.Pattern messagePattern = java.util.regex.Pattern.compile("message\\s+(\\w+)\\s*\\{");
        java.util.regex.Matcher matcher = messagePattern.matcher(proposedSchema);

        if (matcher.find()) {
            String messageName = matcher.group(1);
            int messageEnd = currentSchema.lastIndexOf("}");

            java.util.regex.Pattern fieldPattern = java.util.regex.Pattern.compile(
                    "(required|optional|repeated)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*(\\d+)");
            java.util.regex.Matcher fieldMatcher = fieldPattern.matcher(proposedSchema);

            while (fieldMatcher.find()) {
                int tag = Integer.parseInt(fieldMatcher.group(4));
                if (!currentTags.contains(tag)) {
                    String rule = fieldMatcher.group(1);
                    String type = fieldMatcher.group(2);
                    String name = fieldMatcher.group(3);

                    if ("required".equals(rule)) {
                        rule = "optional";
                        appliedChanges.add("Changed new field '" + name + "' from required to optional");
                    }

                    String newField = String.format("    %s %s %s = %d;\n", rule, type, name, nextTag);
                    evolvedSchema.insert(messageEnd, newField);
                    appliedChanges.add("Added new field '" + name + "' with tag " + nextTag);
                    nextTag++;
                }
            }
        }

        return evolvedSchema.toString();
    }

    private Set<Integer> extractProtobufTags(String schema) {
        Set<Integer> tags = new HashSet<>();
        java.util.regex.Pattern fieldPattern = java.util.regex.Pattern.compile("=\\s*(\\d+)");
        java.util.regex.Matcher matcher = fieldPattern.matcher(schema);
        while (matcher.find()) {
            tags.add(Integer.parseInt(matcher.group(1)));
        }
        return tags;
    }

    private Integer createNewVersion(SchemaEntity schema, SchemaVersion latestVersion,
                                     String schemaText, List<String> changes, String username) {
        SchemaVersion newVersion = new SchemaVersion();
        newVersion.setVersion(latestVersion.getVersion() + 1);
        newVersion.setSchemaText(schemaText);
        newVersion.setSchema(schema);
        newVersion.setCreatedBy(username);
        newVersion.setAutoGenerated(true);
        newVersion.setDescription("Auto-evolved: " + String.join("; ", changes));

        SchemaVersion saved = versionRepository.save(newVersion);

        auditService.logVersionAutoGenerated(
                schema.getSubject(),
                saved.getVersion(),
                latestVersion.getSchemaText(),
                schemaText,
                String.join("; ", changes)
        );

        return saved.getVersion();
    }

    public EvolutionResult previewEvolution(String subject, String proposedSchema) {
        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));

        SchemaVersion latestVersion = versionRepository.findMaxVersionBySchemaId(schema.getId())
                .flatMap(maxVer -> versionRepository.findBySubjectAndVersion(subject, maxVer))
                .orElseThrow(() -> new RuntimeException("No version found for schema: " + subject));

        String currentSchema = latestVersion.getSchemaText();
        List<String> appliedChanges = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        try {
            String evolvedSchema = evolveSchema(currentSchema, proposedSchema, schema.getType(), appliedChanges, warnings);

            CompatibilityResult compatibilityResult = schemaService.checkCompatibility(
                    schema.getType(),
                    currentSchema,
                    evolvedSchema,
                    schema.getCompatibilityLevel()
            );

            return EvolutionResult.builder()
                    .success(compatibilityResult.isCompatible())
                    .compatible(compatibilityResult.isCompatible())
                    .subject(subject)
                    .oldVersion(latestVersion.getVersion())
                    .oldSchema(currentSchema)
                    .newSchema(evolvedSchema)
                    .appliedChanges(appliedChanges)
                    .warnings(warnings)
                    .message("Preview: " + appliedChanges.size() + " changes would be applied")
                    .compatibilityResult(compatibilityResult)
                    .build();

        } catch (Exception e) {
            return EvolutionResult.builder()
                    .success(false)
                    .compatible(false)
                    .subject(subject)
                    .oldVersion(latestVersion.getVersion())
                    .message("Preview failed: " + e.getMessage())
                    .warnings(Collections.singletonList(e.getMessage()))
                    .build();
        }
    }
}

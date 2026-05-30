package com.api.validator.service;

import com.api.validator.model.FixSuggestion;
import com.api.validator.model.ValidationResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class FixSuggestionService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<FixSuggestion> generateFixSuggestions(ValidationResult validationResult,
                                                       String responseBody,
                                                       JsonNode jsonSchema) {
        List<FixSuggestion> suggestions = new ArrayList<>();

        if (validationResult == null || validationResult.getErrors() == null) {
            return suggestions;
        }

        for (ValidationResult.ValidationError error : validationResult.getErrors()) {
            FixSuggestion suggestion = generateFixForError(error, responseBody, jsonSchema);
            if (suggestion != null) {
                suggestions.add(suggestion);
            }
        }

        suggestions.sort((a, b) -> {
            int orderA = getSeverityOrder(a.getSeverity());
            int orderB = getSeverityOrder(b.getSeverity());
            return Integer.compare(orderB, orderA);
        });

        return suggestions;
    }

    private FixSuggestion generateFixForError(ValidationResult.ValidationError error,
                                                String responseBody,
                                                JsonNode jsonSchema) {
        switch (error.getType()) {
            case REQUIRED_FIELD_MISSING:
                return generateRequiredFieldFix(error, jsonSchema);
            case TYPE_MISMATCH:
                return generateTypeMismatchFix(error, responseBody, jsonSchema);
            case FORMAT_INVALID:
                return generateFormatFix(error, jsonSchema);
            case UNKNOWN_FIELD:
                return generateUnknownFieldFix(error, responseBody);
            case STRUCTURE_INVALID:
                return generateStructureFix(error, jsonSchema);
            case SCHEMA_ERROR:
                return generateSchemaErrorFix(error);
            default:
                return null;
        }
    }

    private FixSuggestion generateRequiredFieldFix(ValidationResult.ValidationError error, JsonNode jsonSchema) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.ADD_MISSING_FIELD);
        suggestion.setSeverity(FixSuggestion.Severity.CRITICAL);
        suggestion.setDescription(String.format("添加缺失的必填字段 '%s'", error.getField()));

        JsonNode fieldSchema = findFieldSchema(jsonSchema, error.getField());
        if (fieldSchema != null) {
            String mockValue = generateMockValue(fieldSchema);
            suggestion.setSuggestedFix(mockValue);
            suggestion.setCodeSnippet(generateAddFieldSnippet(error.getField(), mockValue));

            if (fieldSchema.has("description")) {
                suggestion.addAlternative(String.format("字段说明: %s", fieldSchema.get("description").asText()));
            }

            if (fieldSchema.has("enum")) {
                List<String> enumValues = new ArrayList<>();
                fieldSchema.get("enum").forEach(n -> enumValues.add(n.asText()));
                suggestion.addAlternative(String.format("可使用枚举值: %s", String.join(", ", enumValues)));
            }
        } else {
            suggestion.setSuggestedFix("null");
            suggestion.setCodeSnippet(generateAddFieldSnippet(error.getField(), "null"));
        }

        suggestion.addAlternative("检查是否为接口版本差异导致的字段遗漏");
        suggestion.addAlternative("如果该字段确实不需要，考虑在Schema中移除required约束");

        return suggestion;
    }

    private FixSuggestion generateTypeMismatchFix(ValidationResult.ValidationError error,
                                                    String responseBody,
                                                    JsonNode jsonSchema) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.FIX_TYPE_MISMATCH);
        suggestion.setSeverity(FixSuggestion.Severity.HIGH);
        suggestion.setDescription(String.format("修复字段 '%s' 的类型不匹配", error.getField()));

        try {
            JsonNode responseNode = objectMapper.readTree(responseBody);
            JsonNode fieldValue = findFieldValue(responseNode, error.getField());
            if (fieldValue != null) {
                suggestion.setOriginalValue(fieldValue.toString());
            }
        } catch (Exception ignored) {
        }

        JsonNode fieldSchema = findFieldSchema(jsonSchema, error.getField());
        if (fieldSchema != null) {
            String expectedType = fieldSchema.has("type") ? fieldSchema.get("type").asText() : "string";
            String mockValue = generateMockValue(fieldSchema);

            suggestion.setSuggestedFix(mockValue);
            suggestion.setCodeSnippet(generateTypeFixSnippet(error.getField(), expectedType, mockValue));

            switch (expectedType) {
                case "integer":
                    suggestion.addAlternative("将字符串转换为整数: Integer.parseInt(value)");
                    suggestion.addAlternative("检查是否返回了带引号的数字值");
                    break;
                case "number":
                    suggestion.addAlternative("将字符串转换为数值: Double.parseDouble(value)");
                    suggestion.addAlternative("检查是否返回了带引号的数字值");
                    break;
                case "string":
                    suggestion.addAlternative("将数值转换为字符串: String.valueOf(value)");
                    break;
                case "boolean":
                    suggestion.addAlternative("确保返回布尔值而非字符串 'true'/'false'");
                    break;
                case "object":
                    suggestion.addAlternative("确保该字段返回JSON对象而非基本类型");
                    break;
                case "array":
                    suggestion.addAlternative("确保该字段返回JSON数组");
                    break;
            }
        }

        return suggestion;
    }

    private FixSuggestion generateFormatFix(ValidationResult.ValidationError error, JsonNode jsonSchema) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.FIX_FORMAT);
        suggestion.setSeverity(FixSuggestion.Severity.MEDIUM);
        suggestion.setDescription(String.format("修复字段 '%s' 的格式问题", error.getField()));

        JsonNode fieldSchema = findFieldSchema(jsonSchema, error.getField());
        if (fieldSchema != null) {
            String format = fieldSchema.has("format") ? fieldSchema.get("format").asText() : null;
            String pattern = fieldSchema.has("pattern") ? fieldSchema.get("pattern").asText() : null;

            if (format != null) {
                String formatExample = getFormatExample(format);
                suggestion.setSuggestedFix(formatExample);
                suggestion.setCodeSnippet(generateAddFieldSnippet(error.getField(), formatExample));

                switch (format) {
                    case "email":
                        suggestion.addAlternative("确保邮箱格式符合: user@domain.com");
                        break;
                    case "date-time":
                        suggestion.addAlternative("确保日期时间格式为ISO 8601: 2025-01-15T10:30:00Z");
                        break;
                    case "date":
                        suggestion.addAlternative("确保日期格式为: YYYY-MM-DD");
                        break;
                    case "uri":
                        suggestion.addAlternative("确保URI格式有效，包含协议前缀: https://...");
                        break;
                    case "uuid":
                        suggestion.addAlternative("确保UUID格式有效: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx");
                        break;
                }
            }

            if (pattern != null) {
                suggestion.addAlternative(String.format("需匹配正则模式: %s", pattern));
            }

            if (fieldSchema.has("minimum")) {
                suggestion.addAlternative(String.format("数值不能小于: %s", fieldSchema.get("minimum")));
            }
            if (fieldSchema.has("maximum")) {
                suggestion.addAlternative(String.format("数值不能大于: %s", fieldSchema.get("maximum")));
            }
            if (fieldSchema.has("minLength")) {
                suggestion.addAlternative(String.format("字符串最短: %s 字符", fieldSchema.get("minLength")));
            }
            if (fieldSchema.has("maxLength")) {
                suggestion.addAlternative(String.format("字符串最长: %s 字符", fieldSchema.get("maxLength")));
            }

            if (fieldSchema.has("enum")) {
                List<String> enumValues = new ArrayList<>();
                fieldSchema.get("enum").forEach(n -> enumValues.add(n.asText()));
                suggestion.addAlternative(String.format("允许的枚举值: %s", String.join(", ", enumValues)));
            }
        }

        return suggestion;
    }

    private FixSuggestion generateUnknownFieldFix(ValidationResult.ValidationError error, String responseBody) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.REMOVE_EXTRA_FIELD);
        suggestion.setSeverity(FixSuggestion.Severity.MEDIUM);
        suggestion.setDescription(String.format("移除未定义的字段 '%s'", error.getField()));

        try {
            JsonNode responseNode = objectMapper.readTree(responseBody);
            JsonNode fieldValue = findFieldValue(responseNode, error.getField());
            if (fieldValue != null) {
                suggestion.setOriginalValue(fieldValue.toString());
            }
        } catch (Exception ignored) {
        }

        suggestion.setSuggestedFix("移除该字段");
        suggestion.addAlternative("在Schema的additionalProperties中允许额外字段");
        suggestion.addAlternative("如果该字段需要，将其添加到Schema的properties定义中");

        return suggestion;
    }

    private FixSuggestion generateStructureFix(ValidationResult.ValidationError error, JsonNode jsonSchema) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.FIX_STRUCTURE);
        suggestion.setSeverity(FixSuggestion.Severity.HIGH);
        suggestion.setDescription(String.format("修复字段 '%s' 的结构问题", error.getField()));

        JsonNode fieldSchema = findFieldSchema(jsonSchema, error.getField());
        if (fieldSchema != null) {
            String mockValue = generateMockValue(fieldSchema);
            suggestion.setSuggestedFix(mockValue);
            suggestion.setCodeSnippet(generateAddFieldSnippet(error.getField(), mockValue));
        }

        suggestion.addAlternative("检查响应数据是否被意外嵌套或解包");
        suggestion.addAlternative("确认API返回的数据结构与Schema定义一致");

        return suggestion;
    }

    private FixSuggestion generateSchemaErrorFix(ValidationResult.ValidationError error) {
        FixSuggestion suggestion = new FixSuggestion();
        suggestion.setField(error.getField());
        suggestion.setFixType(FixSuggestion.FixType.FIX_STRUCTURE);
        suggestion.setSeverity(FixSuggestion.Severity.HIGH);
        suggestion.setDescription("Schema校验错误");
        suggestion.setSuggestedFix("检查OpenAPI规范定义是否正确");
        suggestion.addAlternative("确认Schema语法符合JSON Schema Draft-07规范");
        suggestion.addAlternative("检查$ref引用是否正确解析");

        return suggestion;
    }

    public String generateFixedResponse(String responseBody, List<FixSuggestion> suggestions, JsonNode jsonSchema) {
        try {
            JsonNode responseNode = objectMapper.readTree(responseBody);
            JsonNode fixedNode = applyFixes(responseNode, suggestions, jsonSchema);
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(fixedNode);
        } catch (Exception e) {
            return responseBody;
        }
    }

    private JsonNode applyFixes(JsonNode responseNode, List<FixSuggestion> suggestions, JsonNode jsonSchema) {
        ObjectNode fixedNode = responseNode.deepCopy();

        for (FixSuggestion suggestion : suggestions) {
            if (suggestion.getFixType() == FixSuggestion.FixType.ADD_MISSING_FIELD) {
                String fieldPath = suggestion.getField();
                JsonNode fieldSchema = findFieldSchema(jsonSchema, fieldPath);

                if (fieldPath.contains(".")) {
                    String[] parts = fieldPath.split("\\.");
                    ObjectNode current = fixedNode;
                    for (int i = 0; i < parts.length - 1; i++) {
                        if (!current.has(parts[i])) {
                            current.set(parts[i], objectMapper.createObjectNode());
                        }
                        current = (ObjectNode) current.get(parts[i]);
                    }
                    if (!current.has(parts[parts.length - 1]) && fieldSchema != null) {
                        current.set(parts[parts.length - 1], generateMockNode(fieldSchema));
                    }
                } else {
                    if (!fixedNode.has(fieldPath) && fieldSchema != null) {
                        fixedNode.set(fieldPath, generateMockNode(fieldSchema));
                    }
                }
            } else if (suggestion.getFixType() == FixSuggestion.FixType.REMOVE_EXTRA_FIELD) {
                String fieldPath = suggestion.getField();
                if (fieldPath.contains(".")) {
                    String[] parts = fieldPath.split("\\.");
                    ObjectNode current = fixedNode;
                    for (int i = 0; i < parts.length - 1; i++) {
                        if (current.has(parts[i])) {
                            current = (ObjectNode) current.get(parts[i]);
                        }
                    }
                    if (current != null) {
                        current.remove(parts[parts.length - 1]);
                    }
                } else {
                    fixedNode.remove(fieldPath);
                }
            } else if (suggestion.getFixType() == FixSuggestion.FixType.FIX_TYPE_MISMATCH) {
                JsonNode fieldSchema = findFieldSchema(jsonSchema, suggestion.getField());
                if (fieldSchema != null) {
                    String fieldPath = suggestion.getField();
                    if (fieldPath.contains(".")) {
                        String[] parts = fieldPath.split("\\.");
                        ObjectNode current = fixedNode;
                        for (int i = 0; i < parts.length - 1; i++) {
                            if (current.has(parts[i])) {
                                current = (ObjectNode) current.get(parts[i]);
                            }
                        }
                        if (current != null) {
                            current.set(parts[parts.length - 1], generateMockNode(fieldSchema));
                        }
                    } else {
                        fixedNode.set(fieldPath, generateMockNode(fieldSchema));
                    }
                }
            }
        }

        return fixedNode;
    }

    private JsonNode generateMockNode(JsonNode schema) {
        if (schema == null) {
            return objectMapper.getNodeFactory().nullNode();
        }

        String type = schema.has("type") ? schema.get("type").asText() : "string";

        switch (type) {
            case "object":
                ObjectNode objNode = objectMapper.createObjectNode();
                if (schema.has("properties")) {
                    JsonNode props = schema.get("properties");
                    props.fieldNames().forEachRemaining(name -> {
                        JsonNode propSchema = props.get(name);
                        objNode.set(name, generateMockNode(propSchema));
                    });
                }
                return objNode;
            case "array":
                ArrayNode arrNode = objectMapper.createArrayNode();
                if (schema.has("items")) {
                    arrNode.add(generateMockNode(schema.get("items")));
                }
                return arrNode;
            case "string":
                if (schema.has("enum")) {
                    return objectMapper.getNodeFactory().textNode(schema.get("enum").get(0).asText());
                }
                if (schema.has("format")) {
                    return objectMapper.getNodeFactory().textNode(getFormatExample(schema.get("format").asText()));
                }
                return objectMapper.getNodeFactory().textNode("mock_value");
            case "integer":
                return objectMapper.getNodeFactory().numberNode(0);
            case "number":
                return objectMapper.getNodeFactory().numberNode(0.0);
            case "boolean":
                return objectMapper.getNodeFactory().booleanNode(false);
            default:
                return objectMapper.getNodeFactory().nullNode();
        }
    }

    private JsonNode findFieldSchema(JsonNode schema, String fieldPath) {
        if (schema == null || fieldPath == null || fieldPath.isEmpty()) {
            return schema;
        }

        String[] parts = fieldPath.split("\\.");
        JsonNode current = schema;

        for (String part : parts) {
            if (current == null) return null;

            if (current.has("properties") && current.get("properties").has(part)) {
                current = current.get("properties").get(part);
            } else if (current.has("items")) {
                current = current.get("items");
                if (current.has("properties") && current.get("properties").has(part)) {
                    current = current.get("properties").get(part);
                } else {
                    return null;
                }
            } else {
                return null;
            }
        }

        return current;
    }

    private JsonNode findFieldValue(JsonNode responseNode, String fieldPath) {
        if (responseNode == null || fieldPath == null || fieldPath.isEmpty()) {
            return responseNode;
        }

        String[] parts = fieldPath.split("\\.");
        JsonNode current = responseNode;

        for (String part : parts) {
            if (current == null) return null;
            if (current.isObject() && current.has(part)) {
                current = current.get(part);
            } else {
                return null;
            }
        }

        return current;
    }

    private String generateMockValue(JsonNode schema) {
        if (schema == null) return "null";

        String type = schema.has("type") ? schema.get("type").asText() : "string";

        if (schema.has("enum")) {
            return "\"" + schema.get("enum").get(0).asText() + "\"";
        }

        switch (type) {
            case "string":
                if (schema.has("format")) {
                    return "\"" + getFormatExample(schema.get("format").asText()) + "\"";
                }
                return "\"mock_value\"";
            case "integer":
                return "0";
            case "number":
                return "0.0";
            case "boolean":
                return "false";
            case "object":
                return "{}";
            case "array":
                return "[]";
            default:
                return "null";
        }
    }

    private String getFormatExample(String format) {
        return switch (format) {
            case "email" -> "user@example.com";
            case "date-time" -> "2025-01-15T10:30:00Z";
            case "date" -> "2025-01-15";
            case "time" -> "10:30:00";
            case "uri", "url" -> "https://example.com";
            case "uuid" -> "550e8400-e29b-41d4-a716-446655440000";
            case "ipv4" -> "192.168.1.1";
            case "hostname" -> "example.com";
            default -> "mock_" + format;
        };
    }

    private String generateAddFieldSnippet(String field, String value) {
        return String.format("\"%s\": %s", field, value);
    }

    private String generateTypeFixSnippet(String field, String expectedType, String value) {
        return String.format("// 期望类型: %s\n\"%s\": %s", expectedType, field, value);
    }

    private int getSeverityOrder(FixSuggestion.Severity severity) {
        if (severity == null) return 0;
        switch (severity) {
            case CRITICAL: return 4;
            case HIGH: return 3;
            case MEDIUM: return 2;
            case LOW: return 1;
            default: return 0;
        }
    }
}

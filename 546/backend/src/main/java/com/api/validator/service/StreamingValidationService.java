package com.api.validator.service;

import com.api.validator.model.ValidationResult;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.StringReader;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class StreamingValidationService {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final JsonFactory jsonFactory = new JsonFactory();

    public ValidationResult validateStreaming(String responseBody, JsonNode jsonSchema) {
        ValidationResult result = new ValidationResult();
        result.setValid(true);

        try (StringReader reader = new StringReader(responseBody);
             JsonParser parser = jsonFactory.createParser(reader)) {

            parser.nextToken();
            validateNodeStreaming(parser, jsonSchema, "", result, new HashSet<>());

            checkRequiredFields(jsonSchema, "", result);

        } catch (IOException e) {
            result.setValid(false);
            result.addError("", "JSON解析错误: " + e.getMessage(), 
                    ValidationResult.ErrorType.STRUCTURE_INVALID, ValidationResult.Severity.CRITICAL);
        } catch (Exception e) {
            result.setValid(false);
            result.addError("", "校验错误: " + e.getMessage(), 
                    ValidationResult.ErrorType.SCHEMA_ERROR, ValidationResult.Severity.HIGH);
        }

        result.sortErrorsBySeverity();
        return result;
    }

    private void validateNodeStreaming(JsonParser parser, JsonNode schemaNode, String path, 
                                        ValidationResult result, Set<String> visitedFields) throws IOException {
        if (schemaNode == null || !schemaNode.has("type")) {
            skipCurrentValue(parser);
            return;
        }

        String expectedType = schemaNode.get("type").asText();
        JsonToken currentToken = parser.currentToken();

        if (!matchesType(currentToken, expectedType)) {
            String actualType = getTypeFromToken(currentToken);
            result.addError(path.isEmpty() ? "root" : path, 
                    String.format("类型不匹配: 期望 %s, 实际 %s", expectedType, actualType),
                    ValidationResult.ErrorType.TYPE_MISMATCH,
                    ValidationResult.Severity.HIGH);
            skipCurrentValue(parser);
            return;
        }

        switch (expectedType) {
            case "object":
                validateObjectStreaming(parser, schemaNode, path, result, visitedFields);
                break;
            case "array":
                validateArrayStreaming(parser, schemaNode, path, result, visitedFields);
                break;
            case "string":
                validateStringStreaming(parser, schemaNode, path, result);
                break;
            case "integer":
            case "number":
                validateNumberStreaming(parser, schemaNode, path, result, expectedType);
                break;
            case "boolean":
                parser.nextToken();
                break;
            default:
                skipCurrentValue(parser);
        }
    }

    private void validateObjectStreaming(JsonParser parser, JsonNode schemaNode, String path,
                                          ValidationResult result, Set<String> visitedFields) throws IOException {
        JsonNode properties = schemaNode.has("properties") ? schemaNode.get("properties") : null;
        Set<String> allowedFields = new HashSet<>();
        
        if (properties != null) {
            properties.fieldNames().forEachRemaining(allowedFields::add);
        }

        while (parser.nextToken() != JsonToken.END_OBJECT) {
            String fieldName = parser.getCurrentName();
            parser.nextToken();

            String fieldPath = path.isEmpty() ? fieldName : path + "." + fieldName;
            visitedFields.add(fieldPath);

            if (allowedFields.isEmpty() || allowedFields.contains(fieldName)) {
                if (properties != null && properties.has(fieldName)) {
                    JsonNode fieldSchema = properties.get(fieldName);
                    validateNodeStreaming(parser, fieldSchema, fieldPath, result, new HashSet<>());
                } else {
                    skipCurrentValue(parser);
                }
            } else {
                result.addError(fieldPath, 
                        String.format("未知字段 '%s'", fieldName),
                        ValidationResult.ErrorType.UNKNOWN_FIELD,
                        ValidationResult.Severity.MEDIUM);
                skipCurrentValue(parser);
            }
        }
    }

    private void validateArrayStreaming(JsonParser parser, JsonNode schemaNode, String path,
                                         ValidationResult result, Set<String> visitedFields) throws IOException {
        JsonNode itemSchema = schemaNode.has("items") ? schemaNode.get("items") : null;
        int index = 0;

        while (parser.nextToken() != JsonToken.END_ARRAY) {
            String itemPath = (path.isEmpty() ? "root" : path) + "[" + index + "]";
            if (itemSchema != null) {
                validateNodeStreaming(parser, itemSchema, itemPath, result, new HashSet<>());
            } else {
                skipCurrentValue(parser);
            }
            index++;
        }

        if (schemaNode.has("minItems")) {
            int minItems = schemaNode.get("minItems").asInt();
            if (index < minItems) {
                result.addError(path.isEmpty() ? "root" : path,
                        String.format("数组长度 %d 小于最小值 %d", index, minItems),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }

        if (schemaNode.has("maxItems")) {
            int maxItems = schemaNode.get("maxItems").asInt();
            if (index > maxItems) {
                result.addError(path.isEmpty() ? "root" : path,
                        String.format("数组长度 %d 大于最大值 %d", index, maxItems),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }
    }

    private void validateStringStreaming(JsonParser parser, JsonNode schemaNode, String path,
                                          ValidationResult result) throws IOException {
        String value = parser.getValueAsString();
        parser.nextToken();

        if (schemaNode.has("minLength")) {
            int minLength = schemaNode.get("minLength").asInt();
            if (value.length() < minLength) {
                result.addError(path,
                        String.format("字符串长度 %d 小于最小值 %d", value.length(), minLength),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }

        if (schemaNode.has("maxLength")) {
            int maxLength = schemaNode.get("maxLength").asInt();
            if (value.length() > maxLength) {
                result.addError(path,
                        String.format("字符串长度 %d 大于最大值 %d", value.length(), maxLength),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }

        if (schemaNode.has("pattern")) {
            String pattern = schemaNode.get("pattern").asText();
            if (!value.matches(pattern)) {
                result.addError(path,
                        String.format("字符串格式不匹配正则表达式: %s", pattern),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }

        if (schemaNode.has("format")) {
            String format = schemaNode.get("format").asText();
            validateStringFormat(value, format, path, result);
        }

        if (schemaNode.has("enum")) {
            List<String> allowedValues = new ArrayList<>();
            schemaNode.get("enum").forEach(node -> allowedValues.add(node.asText()));
            if (!allowedValues.contains(value)) {
                result.addError(path,
                        String.format("值 '%s' 不在允许的枚举列表中: %s", value, allowedValues),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.HIGH);
            }
        }
    }

    private void validateNumberStreaming(JsonParser parser, JsonNode schemaNode, String path,
                                          ValidationResult result, String expectedType) throws IOException {
        double value;
        
        if (parser.currentToken() == JsonToken.VALUE_NUMBER_INT) {
            value = parser.getLongValue();
        } else {
            value = parser.getDoubleValue();
        }
        parser.nextToken();

        if ("integer".equals(expectedType) && parser.currentToken() != null && 
            parser.currentToken() == JsonToken.VALUE_NUMBER_FLOAT) {
            result.addError(path,
                    "类型不匹配: 期望 integer, 实际 number",
                    ValidationResult.ErrorType.TYPE_MISMATCH,
                    ValidationResult.Severity.HIGH);
        }

        if (schemaNode.has("minimum")) {
            double minimum = schemaNode.get("minimum").asDouble();
            if (value < minimum) {
                result.addError(path,
                        String.format("数值 %.2f 小于最小值 %.2f", value, minimum),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }

        if (schemaNode.has("maximum")) {
            double maximum = schemaNode.get("maximum").asDouble();
            if (value > maximum) {
                result.addError(path,
                        String.format("数值 %.2f 大于最大值 %.2f", value, maximum),
                        ValidationResult.ErrorType.FORMAT_INVALID,
                        ValidationResult.Severity.MEDIUM);
            }
        }
    }

    private void validateStringFormat(String value, String format, String path, ValidationResult result) {
        switch (format) {
            case "email":
                if (!value.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$")) {
                    result.addError(path, "邮箱格式无效", 
                            ValidationResult.ErrorType.FORMAT_INVALID, ValidationResult.Severity.MEDIUM);
                }
                break;
            case "date-time":
                if (!value.matches("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$")) {
                    result.addError(path, "日期时间格式无效，期望 ISO 8601 格式", 
                            ValidationResult.ErrorType.FORMAT_INVALID, ValidationResult.Severity.MEDIUM);
                }
                break;
            case "date":
                if (!value.matches("^\\d{4}-\\d{2}-\\d{2}$")) {
                    result.addError(path, "日期格式无效，期望 YYYY-MM-DD 格式", 
                            ValidationResult.ErrorType.FORMAT_INVALID, ValidationResult.Severity.MEDIUM);
                }
                break;
            case "uri":
                if (!value.matches("^https?://.+")) {
                    result.addError(path, "URI格式无效", 
                            ValidationResult.ErrorType.FORMAT_INVALID, ValidationResult.Severity.MEDIUM);
                }
                break;
        }
    }

    private void checkRequiredFields(JsonNode schemaNode, String path, ValidationResult result) {
        if (schemaNode == null || !schemaNode.has("required")) {
            return;
        }

        List<String> requiredFields = new ArrayList<>();
        schemaNode.get("required").forEach(node -> requiredFields.add(node.asText()));

        for (String field : requiredFields) {
            String fieldPath = path.isEmpty() ? field : path + "." + field;
            result.addError(fieldPath, 
                    String.format("必填字段 '%s' 缺失", field),
                    ValidationResult.ErrorType.REQUIRED_FIELD_MISSING,
                    ValidationResult.Severity.CRITICAL);
        }

        if (schemaNode.has("properties")) {
            JsonNode properties = schemaNode.get("properties");
            properties.fieldNames().forEachRemaining(fieldName -> {
                JsonNode fieldSchema = properties.get(fieldName);
                if (fieldSchema.has("type") && "object".equals(fieldSchema.get("type").asText())) {
                    String nestedPath = path.isEmpty() ? fieldName : path + "." + fieldName;
                    checkRequiredFields(fieldSchema, nestedPath, result);
                }
            });
        }
    }

    private void skipCurrentValue(JsonParser parser) throws IOException {
        if (parser.currentToken() == JsonToken.START_OBJECT) {
            int depth = 1;
            while (depth > 0 && parser.nextToken() != null) {
                if (parser.currentToken() == JsonToken.START_OBJECT) depth++;
                else if (parser.currentToken() == JsonToken.END_OBJECT) depth--;
            }
        } else if (parser.currentToken() == JsonToken.START_ARRAY) {
            int depth = 1;
            while (depth > 0 && parser.nextToken() != null) {
                if (parser.currentToken() == JsonToken.START_ARRAY) depth++;
                else if (parser.currentToken() == JsonToken.END_ARRAY) depth--;
            }
        } else {
            parser.nextToken();
        }
    }

    private boolean matchesType(JsonToken token, String expectedType) {
        if (token == null) return false;
        
        switch (expectedType) {
            case "object":
                return token == JsonToken.START_OBJECT;
            case "array":
                return token == JsonToken.START_ARRAY;
            case "string":
                return token == JsonToken.VALUE_STRING;
            case "integer":
                return token == JsonToken.VALUE_NUMBER_INT;
            case "number":
                return token == JsonToken.VALUE_NUMBER_INT || token == JsonToken.VALUE_NUMBER_FLOAT;
            case "boolean":
                return token == JsonToken.VALUE_TRUE || token == JsonToken.VALUE_FALSE;
            case "null":
                return token == JsonToken.VALUE_NULL;
            default:
                return true;
        }
    }

    private String getTypeFromToken(JsonToken token) {
        if (token == null) return "null";
        switch (token) {
            case START_OBJECT: return "object";
            case START_ARRAY: return "array";
            case VALUE_STRING: return "string";
            case VALUE_NUMBER_INT: return "integer";
            case VALUE_NUMBER_FLOAT: return "number";
            case VALUE_TRUE:
            case VALUE_FALSE: return "boolean";
            case VALUE_NULL: return "null";
            default: return "unknown";
        }
    }

}

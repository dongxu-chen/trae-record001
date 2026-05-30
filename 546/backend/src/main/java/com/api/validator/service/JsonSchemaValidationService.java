package com.api.validator.service;

import com.api.validator.model.ValidationResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.everit.json.schema.Schema;
import org.everit.json.schema.ValidationException;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class JsonSchemaValidationService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public ValidationResult validate(String responseBody, JsonNode jsonSchema) {
        ValidationResult result = new ValidationResult();
        result.setValid(true);

        try {
            JSONObject schemaJson = new JSONObject(jsonSchema.toString());
            SchemaLoader loader = SchemaLoader.builder()
                    .schemaJson(schemaJson)
                    .draftV7Support()
                    .build();
            Schema schema = loader.load().build();

            JSONObject responseJson = new JSONObject(new JSONTokener(responseBody));
            schema.validate(responseJson);

        } catch (ValidationException e) {
            result.setValid(false);
            processValidationException(e, result, "");
        } catch (Exception e) {
            result.setValid(false);
            result.addError("", "解析错误: " + e.getMessage(), ValidationResult.ErrorType.SCHEMA_ERROR);
        }

        return result;
    }

    private void processValidationException(ValidationException e, ValidationResult result, String parentPath) {
        List<ValidationException> causes = e.getCausingExceptions();
        
        if (causes.isEmpty()) {
            String fieldPath = buildFieldPath(parentPath, e.getPointerToViolation());
            String message = e.getMessage();
            
            ValidationResult.ErrorType errorType = determineErrorType(message, e.getKeyword());
            result.addError(fieldPath, cleanErrorMessage(message), errorType);
        } else {
            for (ValidationException cause : causes) {
                String currentPath = buildFieldPath(parentPath, e.getPointerToViolation());
                processValidationException(cause, result, currentPath);
            }
        }
    }

    private String buildFieldPath(String parentPath, String pointer) {
        if (pointer == null || pointer.isEmpty()) {
            return parentPath != null && !parentPath.isEmpty() ? parentPath : "root";
        }
        
        String path = pointer.replace("#/", "").replace("/", ".");
        if (parentPath != null && !parentPath.isEmpty() && !parentPath.equals("root")) {
            return parentPath + "." + path;
        }
        return path;
    }

    private ValidationResult.ErrorType determineErrorType(String message, String keyword) {
        if (keyword == null) {
            return ValidationResult.ErrorType.STRUCTURE_INVALID;
        }
        
        return switch (keyword) {
            case "required" -> ValidationResult.ErrorType.REQUIRED_FIELD_MISSING;
            case "type" -> ValidationResult.ErrorType.TYPE_MISMATCH;
            case "format" -> ValidationResult.ErrorType.FORMAT_INVALID;
            case "additionalProperties" -> ValidationResult.ErrorType.UNKNOWN_FIELD;
            default -> ValidationResult.ErrorType.STRUCTURE_INVALID;
        };
    }

    private String cleanErrorMessage(String message) {
        Pattern pattern = Pattern.compile("^.*?:\\s*(.+)$");
        Matcher matcher = pattern.matcher(message);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return message;
    }

    public ValidationResult validateWithCustomChecks(String responseBody, JsonNode jsonSchema) {
        ValidationResult result = validate(responseBody, jsonSchema);
        
        try {
            JsonNode responseNode = objectMapper.readTree(responseBody);
            performAdditionalValidation(responseNode, jsonSchema, "", result);
        } catch (Exception e) {
            result.setValid(false);
            result.addError("", "额外校验错误: " + e.getMessage(), ValidationResult.ErrorType.SCHEMA_ERROR);
        }
        
        result.sortErrorsBySeverity();
        return result;
    }

    private void performAdditionalValidation(JsonNode responseNode, JsonNode schemaNode, String path, ValidationResult result) {
        if (schemaNode == null || !schemaNode.has("type")) {
            return;
        }

        String type = schemaNode.get("type").asText();

        if ("object".equals(type) && schemaNode.has("properties")) {
            JsonNode properties = schemaNode.get("properties");
            properties.fieldNames().forEachRemaining(fieldName -> {
                String fieldPath = path.isEmpty() ? fieldName : path + "." + fieldName;
                if (responseNode.has(fieldName)) {
                    performAdditionalValidation(responseNode.get(fieldName), properties.get(fieldName), fieldPath, result);
                }
            });
        }

        if ("array".equals(type) && schemaNode.has("items") && responseNode.isArray()) {
            JsonNode itemSchema = schemaNode.get("items");
            for (int i = 0; i < responseNode.size(); i++) {
                String itemPath = path + "[" + i + "]";
                performAdditionalValidation(responseNode.get(i), itemSchema, itemPath, result);
            }
        }

        if ("string".equals(type) && schemaNode.has("pattern") && responseNode.isTextual()) {
            String pattern = schemaNode.get("pattern").asText();
            String value = responseNode.asText();
            if (!value.matches(pattern)) {
                result.addError(path, "字符串格式不匹配正则表达式: " + pattern, ValidationResult.ErrorType.FORMAT_INVALID);
            }
        }

        if ("string".equals(type) && schemaNode.has("minLength") && responseNode.isTextual()) {
            int minLength = schemaNode.get("minLength").asInt();
            if (responseNode.asText().length() < minLength) {
                result.addError(path, "字符串长度小于最小值: " + minLength, ValidationResult.ErrorType.FORMAT_INVALID);
            }
        }

        if ("string".equals(type) && schemaNode.has("maxLength") && responseNode.isTextual()) {
            int maxLength = schemaNode.get("maxLength").asInt();
            if (responseNode.asText().length() > maxLength) {
                result.addError(path, "字符串长度大于最大值: " + maxLength, ValidationResult.ErrorType.FORMAT_INVALID);
            }
        }

        if (("integer".equals(type) || "number".equals(type)) && schemaNode.has("minimum") && responseNode.isNumber()) {
            double minimum = schemaNode.get("minimum").asDouble();
            if (responseNode.asDouble() < minimum) {
                result.addError(path, "数值小于最小值: " + minimum, ValidationResult.ErrorType.FORMAT_INVALID);
            }
        }

        if (("integer".equals(type) || "number".equals(type)) && schemaNode.has("maximum") && responseNode.isNumber()) {
            double maximum = schemaNode.get("maximum").asDouble();
            if (responseNode.asDouble() > maximum) {
                result.addError(path, "数值大于最大值: " + maximum, ValidationResult.ErrorType.FORMAT_INVALID);
            }
        }
    }
}

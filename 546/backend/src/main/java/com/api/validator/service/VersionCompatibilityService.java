package com.api.validator.service;

import com.api.validator.model.CompatibilityResult;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class VersionCompatibilityService {

    public CompatibilityResult checkCompatibility(JsonNode oldSchema, JsonNode newSchema,
                                                   String oldVersion, String newVersion,
                                                   String path, String method) {
        CompatibilityResult result = new CompatibilityResult();
        result.setOldVersion(oldVersion);
        result.setNewVersion(newVersion);
        result.setPath(path);
        result.setMethod(method);

        compareSchemas(oldSchema, newSchema, "", result);

        determineCompatibilityLevel(result);

        generateSuggestions(result);

        return result;
    }

    private void compareSchemas(JsonNode oldSchema, JsonNode newSchema, String path, CompatibilityResult result) {
        if (oldSchema == null && newSchema == null) {
            return;
        }

        if (oldSchema == null) {
            result.addIssue(new CompatibilityResult.CompatibilityIssue(
                path,
                CompatibilityResult.IssueType.FIELD_ADDED_OPTIONAL,
                CompatibilityResult.Severity.INFO,
                "新增字段",
                null,
                describeSchema(newSchema)
            ));
            return;
        }

        if (newSchema == null) {
            result.addIssue(new CompatibilityResult.CompatibilityIssue(
                path,
                CompatibilityResult.IssueType.FIELD_REMOVED,
                CompatibilityResult.Severity.BREAKING,
                "字段已删除",
                describeSchema(oldSchema),
                null
            ));
            return;
        }

        String oldType = oldSchema.has("type") ? oldSchema.get("type").asText() : "object";
        String newType = newSchema.has("type") ? newSchema.get("type").asText() : "object";

        if (!oldType.equals(newType)) {
            result.addIssue(new CompatibilityResult.CompatibilityIssue(
                path,
                CompatibilityResult.IssueType.FIELD_TYPE_CHANGED,
                CompatibilityResult.Severity.BREAKING,
                String.format("类型从 '%s' 变为 '%s'", oldType, newType),
                oldType,
                newType
            ));
            return;
        }

        switch (oldType) {
            case "object":
                compareObjectSchemas(oldSchema, newSchema, path, result);
                break;
            case "array":
                compareArraySchemas(oldSchema, newSchema, path, result);
                break;
            case "string":
                compareStringSchemas(oldSchema, newSchema, path, result);
                break;
            case "integer":
            case "number":
                compareNumberSchemas(oldSchema, newSchema, path, result);
                break;
        }
    }

    private void compareObjectSchemas(JsonNode oldSchema, JsonNode newSchema, String path, CompatibilityResult result) {
        JsonNode oldProps = oldSchema.has("properties") ? oldSchema.get("properties") : null;
        JsonNode newProps = newSchema.has("properties") ? newSchema.get("properties") : null;

        Set<String> oldFields = new HashSet<>();
        Set<String> newFields = new HashSet<>();

        if (oldProps != null) {
            oldProps.fieldNames().forEachRemaining(oldFields::add);
        }
        if (newProps != null) {
            newProps.fieldNames().forEachRemaining(newFields::add);
        }

        Set<String> oldRequired = getRequiredFields(oldSchema);
        Set<String> newRequired = getRequiredFields(newSchema);

        for (String field : oldFields) {
            String fieldPath = path.isEmpty() ? field : path + "." + field;
            if (!newFields.contains(field)) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    fieldPath,
                    CompatibilityResult.IssueType.FIELD_REMOVED,
                    CompatibilityResult.Severity.BREAKING,
                    String.format("字段 '%s' 在新版本中被删除", field),
                    describeSchema(oldProps.get(field)),
                    null
                ));
            } else {
                compareSchemas(oldProps.get(field), newProps.get(field), fieldPath, result);
            }
        }

        for (String field : newFields) {
            String fieldPath = path.isEmpty() ? field : path + "." + field;
            if (!oldFields.contains(field)) {
                if (newRequired.contains(field)) {
                    result.addIssue(new CompatibilityResult.CompatibilityIssue(
                        fieldPath,
                        CompatibilityResult.IssueType.REQUIRED_FIELD_ADDED,
                        CompatibilityResult.Severity.BREAKING,
                        String.format("新版本新增了必填字段 '%s'", field),
                        null,
                        describeSchema(newProps.get(field))
                    ));
                } else {
                    result.addIssue(new CompatibilityResult.CompatibilityIssue(
                        fieldPath,
                        CompatibilityResult.IssueType.FIELD_ADDED_OPTIONAL,
                        CompatibilityResult.Severity.INFO,
                        String.format("新版本新增了可选字段 '%s'", field),
                        null,
                        describeSchema(newProps.get(field))
                    ));
                }
            } else {
                boolean wasRequired = oldRequired.contains(field);
                boolean isNowRequired = newRequired.contains(field);
                if (!wasRequired && isNowRequired) {
                    result.addIssue(new CompatibilityResult.CompatibilityIssue(
                        fieldPath,
                        CompatibilityResult.IssueType.REQUIRED_FIELD_ADDED,
                        CompatibilityResult.Severity.BREAKING,
                        String.format("字段 '%s' 从可选变为必填", field),
                        "optional",
                        "required"
                    ));
                }
            }
        }
    }

    private void compareArraySchemas(JsonNode oldSchema, JsonNode newSchema, String path, CompatibilityResult result) {
        JsonNode oldItems = oldSchema.has("items") ? oldSchema.get("items") : null;
        JsonNode newItems = newSchema.has("items") ? newSchema.get("items") : null;

        if (oldItems != null || newItems != null) {
            compareSchemas(oldItems, newItems, path + "[]", result);
        }

        if (oldSchema.has("minItems") && newSchema.has("minItems")) {
            int oldMin = oldSchema.get("minItems").asInt();
            int newMin = newSchema.get("minItems").asInt();
            if (newMin > oldMin) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("数组最小长度从 %d 增加到 %d", oldMin, newMin),
                    String.valueOf(oldMin),
                    String.valueOf(newMin)
                ));
            }
        }

        if (oldSchema.has("maxItems") && newSchema.has("maxItems")) {
            int oldMax = oldSchema.get("maxItems").asInt();
            int newMax = newSchema.get("maxItems").asInt();
            if (newMax < oldMax) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("数组最大长度从 %d 减少到 %d", oldMax, newMax),
                    String.valueOf(oldMax),
                    String.valueOf(newMax)
                ));
            } else if (newMax > oldMax) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_WIDENED,
                    CompatibilityResult.Severity.INFO,
                    String.format("数组最大长度从 %d 增加到 %d", oldMax, newMax),
                    String.valueOf(oldMax),
                    String.valueOf(newMax)
                ));
            }
        }
    }

    private void compareStringSchemas(JsonNode oldSchema, JsonNode newSchema, String path, CompatibilityResult result) {
        if (oldSchema.has("format") && newSchema.has("format")) {
            String oldFormat = oldSchema.get("format").asText();
            String newFormat = newSchema.get("format").asText();
            if (!oldFormat.equals(newFormat)) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.FORMAT_CHANGED,
                    CompatibilityResult.Severity.BREAKING,
                    String.format("字符串格式从 '%s' 变为 '%s'", oldFormat, newFormat),
                    oldFormat,
                    newFormat
                ));
            }
        }

        if (oldSchema.has("enum") && newSchema.has("enum")) {
            Set<String> oldEnum = new HashSet<>();
            Set<String> newEnum = new HashSet<>();
            oldSchema.get("enum").forEach(n -> oldEnum.add(n.asText()));
            newSchema.get("enum").forEach(n -> newEnum.add(n.asText()));

            for (String val : oldEnum) {
                if (!newEnum.contains(val)) {
                    result.addIssue(new CompatibilityResult.CompatibilityIssue(
                        path,
                        CompatibilityResult.IssueType.ENUM_VALUE_REMOVED,
                        CompatibilityResult.Severity.BREAKING,
                        String.format("枚举值 '%s' 在新版本中被移除", val),
                        oldEnum.toString(),
                        newEnum.toString()
                    ));
                }
            }

            for (String val : newEnum) {
                if (!oldEnum.contains(val)) {
                    result.addIssue(new CompatibilityResult.CompatibilityIssue(
                        path,
                        CompatibilityResult.IssueType.ENUM_VALUE_ADDED,
                        CompatibilityResult.Severity.INFO,
                        String.format("新版本新增枚举值 '%s'", val),
                        oldEnum.toString(),
                        newEnum.toString()
                    ));
                }
            }
        }

        if (oldSchema.has("minLength") && newSchema.has("minLength")) {
            int oldMin = oldSchema.get("minLength").asInt();
            int newMin = newSchema.get("minLength").asInt();
            if (newMin > oldMin) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("字符串最小长度从 %d 增加到 %d", oldMin, newMin),
                    String.valueOf(oldMin),
                    String.valueOf(newMin)
                ));
            }
        }

        if (oldSchema.has("maxLength") && newSchema.has("maxLength")) {
            int oldMax = oldSchema.get("maxLength").asInt();
            int newMax = newSchema.get("maxLength").asInt();
            if (newMax < oldMax) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("字符串最大长度从 %d 减少到 %d", oldMax, newMax),
                    String.valueOf(oldMax),
                    String.valueOf(newMax)
                ));
            }
        }

        if (!oldSchema.has("pattern") && newSchema.has("pattern")) {
            result.addIssue(new CompatibilityResult.CompatibilityIssue(
                path,
                CompatibilityResult.IssueType.FIELD_RESTRICTED,
                CompatibilityResult.Severity.WARNING,
                "新版本新增了正则校验模式",
                "无限制",
                newSchema.get("pattern").asText()
            ));
        }
    }

    private void compareNumberSchemas(JsonNode oldSchema, JsonNode newSchema, String path, CompatibilityResult result) {
        if (oldSchema.has("minimum") && newSchema.has("minimum")) {
            double oldMin = oldSchema.get("minimum").asDouble();
            double newMin = newSchema.get("minimum").asDouble();
            if (newMin > oldMin) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("最小值从 %.2f 增加到 %.2f", oldMin, newMin),
                    String.valueOf(oldMin),
                    String.valueOf(newMin)
                ));
            }
        }

        if (oldSchema.has("maximum") && newSchema.has("maximum")) {
            double oldMax = oldSchema.get("maximum").asDouble();
            double newMax = newSchema.get("maximum").asDouble();
            if (newMax < oldMax) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_NARROWED,
                    CompatibilityResult.Severity.WARNING,
                    String.format("最大值从 %.2f 减少到 %.2f", oldMax, newMax),
                    String.valueOf(oldMax),
                    String.valueOf(newMax)
                ));
            } else if (newMax > oldMax) {
                result.addIssue(new CompatibilityResult.CompatibilityIssue(
                    path,
                    CompatibilityResult.IssueType.RANGE_WIDENED,
                    CompatibilityResult.Severity.INFO,
                    String.format("最大值从 %.2f 增加到 %.2f", oldMax, newMax),
                    String.valueOf(oldMax),
                    String.valueOf(newMax)
                ));
            }
        }
    }

    private Set<String> getRequiredFields(JsonNode schema) {
        Set<String> required = new HashSet<>();
        if (schema != null && schema.has("required") && schema.get("required").isArray()) {
            schema.get("required").forEach(n -> required.add(n.asText()));
        }
        return required;
    }

    private void determineCompatibilityLevel(CompatibilityResult result) {
        boolean hasBreaking = false;
        boolean hasWarning = false;

        for (CompatibilityResult.CompatibilityIssue issue : result.getIssues()) {
            if (issue.getSeverity() == CompatibilityResult.Severity.BREAKING) {
                hasBreaking = true;
            } else if (issue.getSeverity() == CompatibilityResult.Severity.WARNING) {
                hasWarning = true;
            }
        }

        if (hasBreaking) {
            result.setCompatibilityLevel(CompatibilityResult.CompatibilityLevel.BREAKING_CHANGE);
            result.setCompatible(false);
        } else if (hasWarning) {
            result.setCompatibilityLevel(CompatibilityResult.CompatibilityLevel.PARTIALLY_COMPATIBLE);
            result.setCompatible(true);
        } else if (!result.getIssues().isEmpty()) {
            result.setCompatibilityLevel(CompatibilityResult.CompatibilityLevel.BACKWARD_COMPATIBLE);
            result.setCompatible(true);
        } else {
            result.setCompatibilityLevel(CompatibilityResult.CompatibilityLevel.FULLY_COMPATIBLE);
            result.setCompatible(true);
        }
    }

    private void generateSuggestions(CompatibilityResult result) {
        for (CompatibilityResult.CompatibilityIssue issue : result.getIssues()) {
            if (issue.getSeverity() == CompatibilityResult.Severity.BREAKING) {
                switch (issue.getIssueType()) {
                    case FIELD_REMOVED:
                        result.addSuggestion(String.format("字段 '%s' 被删除 - 建议在新版本中保留该字段(标记为deprecated)，或提供迁移指南", issue.getField()));
                        break;
                    case FIELD_TYPE_CHANGED:
                        result.addSuggestion(String.format("字段 '%s' 类型变更 - 建议使用独立字段名表示新类型，保留旧字段兼容性", issue.getField()));
                        break;
                    case REQUIRED_FIELD_ADDED:
                        result.addSuggestion(String.format("新增必填字段 '%s' - 建议先作为可选字段引入，下个版本再设为必填", issue.getField()));
                        break;
                    case ENUM_VALUE_REMOVED:
                        result.addSuggestion(String.format("枚举值被移除 - 建议保留旧枚举值并标记为deprecated，或提供值映射方案", issue.getField()));
                        break;
                    case FORMAT_CHANGED:
                        result.addSuggestion(String.format("格式变更 '%s' - 建议使用新字段名存储新格式，旧字段保持原格式", issue.getField()));
                        break;
                    default:
                        break;
                }
            }
        }

        if (result.getCompatibilityLevel() == CompatibilityResult.CompatibilityLevel.BREAKING_CHANGE) {
            result.addSuggestion("检测到破坏性变更！建议使用语义化版本号(SemVer)主版本号升级来标记此变更");
        }
    }

    private String describeSchema(JsonNode schema) {
        if (schema == null) return "null";
        StringBuilder sb = new StringBuilder();
        if (schema.has("type")) {
            sb.append(schema.get("type").asText());
        }
        if (schema.has("format")) {
            sb.append("(").append(schema.get("format").asText()).append(")");
        }
        return sb.length() > 0 ? sb.toString() : "object";
    }
}

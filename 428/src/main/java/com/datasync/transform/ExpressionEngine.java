package com.datasync.transform;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Component
public class ExpressionEngine {

    private final ObjectMapper objectMapper;

    private static final Pattern JSON_PATH_PATTERN = Pattern.compile(
            "JSON_PATH\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*,\\s*['\"]([^'\"]+)['\"]\\s*\\)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern CONCAT_PATTERN = Pattern.compile(
            "CONCAT\\s*\\(([^)]+)\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern SUBSTRING_PATTERN = Pattern.compile(
            "SUBSTRING\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern UPPER_PATTERN = Pattern.compile(
            "UPPER\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern LOWER_PATTERN = Pattern.compile(
            "LOWER\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern LENGTH_PATTERN = Pattern.compile(
            "LENGTH\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern COALESCE_PATTERN = Pattern.compile(
            "COALESCE\\s*\\(([^)]+)\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern IF_PATTERN = Pattern.compile(
            "IF\\s*\\(\\s*([^,]+)\\s*,\\s*([^,]+)\\s*,\\s*([^)]+)\\)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern DATE_FORMAT_PATTERN = Pattern.compile(
            "DATE_FORMAT\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*,\\s*['\"]([^'\"]+)['\"]\\s*\\)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern NOW_PATTERN = Pattern.compile("NOW\\s*\\(\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern TODAY_PATTERN = Pattern.compile("TODAY\\s*\\(\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern MATH_ABS_PATTERN = Pattern.compile(
            "ABS\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*\\)", Pattern.CASE_INSENSITIVE);

    private static final Pattern MATH_ROUND_PATTERN = Pattern.compile(
            "ROUND\\s*\\(\\s*['\"]?([^'\"\\s,]+)['\"]?\\s*(?:,\\s*(\\d+))?\\s*\\)",
            Pattern.CASE_INSENSITIVE);

    private static final Pattern COLUMN_REFERENCE_PATTERN = Pattern.compile("\\$\\{([^}]+)\\}");

    private static final DateTimeFormatter DEFAULT_DATETIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter DEFAULT_DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    public ExpressionEngine(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public Object evaluate(String expression, Map<String, Object> rowData) {
        if (expression == null || expression.trim().isEmpty()) {
            return null;
        }

        String expr = expression.trim();

        try {
            expr = replaceColumnReferences(expr, rowData);

            Matcher jsonPathMatcher = JSON_PATH_PATTERN.matcher(expr);
            if (jsonPathMatcher.find()) {
                return evaluateJsonPath(jsonPathMatcher, rowData);
            }

            Matcher concatMatcher = CONCAT_PATTERN.matcher(expr);
            if (concatMatcher.find()) {
                return evaluateConcat(concatMatcher.group(1), rowData);
            }

            Matcher substringMatcher = SUBSTRING_PATTERN.matcher(expr);
            if (substringMatcher.find()) {
                return evaluateSubstring(substringMatcher, rowData);
            }

            Matcher upperMatcher = UPPER_PATTERN.matcher(expr);
            if (upperMatcher.find()) {
                String value = getStringValue(upperMatcher.group(1), rowData);
                return value != null ? value.toUpperCase() : null;
            }

            Matcher lowerMatcher = LOWER_PATTERN.matcher(expr);
            if (lowerMatcher.find()) {
                String value = getStringValue(lowerMatcher.group(1), rowData);
                return value != null ? value.toLowerCase() : null;
            }

            Matcher lengthMatcher = LENGTH_PATTERN.matcher(expr);
            if (lengthMatcher.find()) {
                String value = getStringValue(lengthMatcher.group(1), rowData);
                return value != null ? value.length() : 0;
            }

            Matcher coalesceMatcher = COALESCE_PATTERN.matcher(expr);
            if (coalesceMatcher.find()) {
                return evaluateCoalesce(coalesceMatcher.group(1), rowData);
            }

            Matcher ifMatcher = IF_PATTERN.matcher(expr);
            if (ifMatcher.find()) {
                return evaluateIf(ifMatcher, rowData);
            }

            Matcher dateFormatMatcher = DATE_FORMAT_PATTERN.matcher(expr);
            if (dateFormatMatcher.find()) {
                return evaluateDateFormat(dateFormatMatcher, rowData);
            }

            Matcher nowMatcher = NOW_PATTERN.matcher(expr);
            if (nowMatcher.find()) {
                return LocalDateTime.now().format(DEFAULT_DATETIME_FORMAT);
            }

            Matcher todayMatcher = TODAY_PATTERN.matcher(expr);
            if (todayMatcher.find()) {
                return LocalDate.now().format(DEFAULT_DATE_FORMAT);
            }

            Matcher absMatcher = MATH_ABS_PATTERN.matcher(expr);
            if (absMatcher.find()) {
                return evaluateAbs(absMatcher.group(1), rowData);
            }

            Matcher roundMatcher = MATH_ROUND_PATTERN.matcher(expr);
            if (roundMatcher.find()) {
                return evaluateRound(roundMatcher, rowData);
            }

            if (isSimpleColumnReference(expr)) {
                return getColumnValue(expr, rowData);
            }

            return expr;

        } catch (Exception e) {
            log.warn("Failed to evaluate expression: {}", expression, e);
            return null;
        }
    }

    private String replaceColumnReferences(String expr, Map<String, Object> rowData) {
        Matcher matcher = COLUMN_REFERENCE_PATTERN.matcher(expr);
        StringBuffer sb = new StringBuffer();

        while (matcher.find()) {
            String columnName = matcher.group(1).trim();
            Object value = rowData.get(columnName);
            String replacement = value != null ? value.toString() : "";
            matcher.appendReplacement(sb, Matcher.quoteReplacement(replacement));
        }

        matcher.appendTail(sb);
        return sb.toString();
    }

    private Object evaluateJsonPath(Matcher matcher, Map<String, Object> rowData) {
        String columnName = matcher.group(1);
        String jsonPath = matcher.group(2);

        Object jsonValue = rowData.get(columnName);
        if (jsonValue == null) {
            return null;
        }

        String jsonString;
        if (jsonValue instanceof String) {
            jsonString = (String) jsonValue;
        } else {
            try {
                jsonString = objectMapper.writeValueAsString(jsonValue);
            } catch (JsonProcessingException e) {
                log.warn("Failed to serialize value to JSON: {}", jsonValue);
                return null;
            }
        }

        return extractJsonPath(jsonString, jsonPath);
    }

    public Object extractJsonPath(String jsonString, String jsonPath) {
        if (jsonString == null || jsonPath == null) {
            return null;
        }

        try {
            JsonNode root = objectMapper.readTree(jsonString);
            String[] pathParts = parseJsonPath(jsonPath);

            JsonNode current = root;
            for (String part : pathParts) {
                if (current == null) {
                    return null;
                }

                if (part.startsWith("[") && part.endsWith("]")) {
                    int index = Integer.parseInt(part.substring(1, part.length() - 1));
                    current = current.get(index);
                } else {
                    current = current.get(part);
                }
            }

            if (current == null) {
                return null;
            }

            return convertJsonNode(current);

        } catch (Exception e) {
            log.warn("Failed to extract JSON path: {} from: {}", jsonPath, jsonString, e);
            return null;
        }
    }

    private String[] parseJsonPath(String jsonPath) {
        String cleanedPath = jsonPath.startsWith("$.") ? jsonPath.substring(2) : jsonPath;
        cleanedPath = cleanedPath.startsWith(".") ? cleanedPath.substring(1) : cleanedPath;
        return cleanedPath.split("\\.");
    }

    private Object convertJsonNode(JsonNode node) {
        if (node.isTextual()) {
            return node.asText();
        } else if (node.isInt() || node.isLong()) {
            return node.asLong();
        } else if (node.isFloat() || node.isDouble()) {
            return node.asDouble();
        } else if (node.isBoolean()) {
            return node.asBoolean();
        } else if (node.isNull()) {
            return null;
        } else {
            try {
                return objectMapper.writeValueAsString(node);
            } catch (JsonProcessingException e) {
                return node.toString();
            }
        }
    }

    private String evaluateConcat(String args, Map<String, Object> rowData) {
        String[] parts = args.split(",");
        StringBuilder sb = new StringBuilder();

        for (String part : parts) {
            String trimmed = part.trim();
            String value = resolveStringValue(trimmed, rowData);
            if (value != null) {
                sb.append(value);
            }
        }

        return sb.toString();
    }

    private String evaluateSubstring(Matcher matcher, Map<String, Object> rowData) {
        String input = getStringValue(matcher.group(1), rowData);
        if (input == null) {
            return null;
        }

        int start = Integer.parseInt(matcher.group(2));
        int length = Integer.parseInt(matcher.group(3));

        start = start <= 0 ? 0 : Math.min(start - 1, input.length());
        int end = Math.min(start + length, input.length());

        return input.substring(start, end);
    }

    private Object evaluateCoalesce(String args, Map<String, Object> rowData) {
        String[] parts = args.split(",");

        for (String part : parts) {
            String trimmed = part.trim();
            Object value = getColumnValue(trimmed, rowData);
            if (value != null) {
                return value;
            }
        }

        return null;
    }

    private Object evaluateIf(Matcher matcher, Map<String, Object> rowData) {
        String condition = matcher.group(1).trim();
        String trueValue = matcher.group(2).trim();
        String falseValue = matcher.group(3).trim();

        boolean result = evaluateCondition(condition, rowData);
        return result ? resolveValue(trueValue, rowData) : resolveValue(falseValue, rowData);
    }

    private boolean evaluateCondition(String condition, Map<String, Object> rowData) {
        if (condition.contains("=") && !condition.contains("==")) {
            String[] parts = condition.split("=", 2);
            Object left = resolveValue(parts[0].trim(), rowData);
            Object right = resolveValue(parts[1].trim(), rowData);
            return left != null && left.equals(right);
        } else if (condition.contains("!=")) {
            String[] parts = condition.split("!=", 2);
            Object left = resolveValue(parts[0].trim(), rowData);
            Object right = resolveValue(parts[1].trim(), rowData);
            return left == null || !left.equals(right);
        } else if (condition.contains(">")) {
            String[] parts = condition.split(">", 2);
            Comparable left = (Comparable) resolveValue(parts[0].trim(), rowData);
            Comparable right = (Comparable) resolveValue(parts[1].trim(), rowData);
            return left != null && right != null && left.compareTo(right) > 0;
        } else if (condition.contains("<")) {
            String[] parts = condition.split("<", 2);
            Comparable left = (Comparable) resolveValue(parts[0].trim(), rowData);
            Comparable right = (Comparable) resolveValue(parts[1].trim(), rowData);
            return left != null && right != null && left.compareTo(right) < 0;
        } else if (condition.toLowerCase().startsWith("is null")) {
            String col = condition.substring(0, condition.toLowerCase().indexOf("is null")).trim();
            return getColumnValue(col, rowData) == null;
        } else if (condition.toLowerCase().startsWith("is not null")) {
            String col = condition.substring(0, condition.toLowerCase().indexOf("is not null")).trim();
            return getColumnValue(col, rowData) != null;
        }

        return false;
    }

    private Object resolveValue(String value, Map<String, Object> rowData) {
        String trimmed = value.trim();

        if (trimmed.startsWith("'") && trimmed.endsWith("'")) {
            return trimmed.substring(1, trimmed.length() - 1);
        }

        if (trimmed.equalsIgnoreCase("null")) {
            return null;
        }

        Object colValue = getColumnValue(trimmed, rowData);
        if (colValue != null) {
            return colValue;
        }

        try {
            return Long.parseLong(trimmed);
        } catch (NumberFormatException e1) {
            try {
                return Double.parseDouble(trimmed);
            } catch (NumberFormatException e2) {
                return trimmed;
            }
        }
    }

    private String resolveStringValue(String value, Map<String, Object> rowData) {
        Object result = resolveValue(value, rowData);
        return result != null ? result.toString() : null;
    }

    private String evaluateDateFormat(Matcher matcher, Map<String, Object> rowData) {
        String columnName = matcher.group(1);
        String formatPattern = matcher.group(2);

        Object value = rowData.get(columnName);
        if (value == null) {
            return null;
        }

        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern(formatPattern);
            if (value instanceof LocalDateTime) {
                return ((LocalDateTime) value).format(formatter);
            } else if (value instanceof LocalDate) {
                return ((LocalDate) value).format(formatter);
            } else {
                String strValue = value.toString();
                LocalDateTime dateTime = LocalDateTime.parse(strValue, DEFAULT_DATETIME_FORMAT);
                return dateTime.format(formatter);
            }
        } catch (Exception e) {
            log.warn("Failed to format date: {}", value, e);
            return value.toString();
        }
    }

    private Object evaluateAbs(String columnName, Map<String, Object> rowData) {
        Object value = rowData.get(columnName);
        if (value == null) {
            return null;
        }

        if (value instanceof Number) {
            if (value instanceof Integer) {
                return Math.abs((Integer) value);
            } else if (value instanceof Long) {
                return Math.abs((Long) value);
            } else if (value instanceof Double) {
                return Math.abs((Double) value);
            } else if (value instanceof BigDecimal) {
                return ((BigDecimal) value).abs();
            }
        }

        return value;
    }

    private Object evaluateRound(Matcher matcher, Map<String, Object> rowData) {
        String columnName = matcher.group(1);
        int scale = matcher.group(2) != null ? Integer.parseInt(matcher.group(2)) : 0;

        Object value = rowData.get(columnName);
        if (value == null) {
            return null;
        }

        if (value instanceof Number) {
            double doubleValue = ((Number) value).doubleValue();
            return Math.round(doubleValue * Math.pow(10, scale)) / Math.pow(10, scale);
        }

        return value;
    }

    private String getStringValue(String columnName, Map<String, Object> rowData) {
        Object value = getColumnValue(columnName, rowData);
        return value != null ? value.toString() : null;
    }

    private Object getColumnValue(String columnName, Map<String, Object> rowData) {
        if (columnName == null) {
            return null;
        }

        String trimmed = columnName.trim();

        if (trimmed.startsWith("'") && trimmed.endsWith("'")) {
            return trimmed.substring(1, trimmed.length() - 1);
        }

        for (Map.Entry<String, Object> entry : rowData.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(trimmed)) {
                return entry.getValue();
            }
        }

        return rowData.get(trimmed);
    }

    private boolean isSimpleColumnReference(String expr) {
        return !expr.contains("(") && !expr.contains(")") && !expr.contains("${");
    }
}

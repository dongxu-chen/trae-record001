package com.log.mask.parser;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.*;
import com.log.mask.core.RegexMaskEngine;

import java.util.*;

public class JsonLogParser implements LogParser {
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Set<String> sensitiveFields = new HashSet<>(Arrays.asList(
            "password", "pwd", "passwd", "pass",
            "idCard", "id_card", "idcard", "身份证",
            "phone", "mobile", "telephone", "手机号", "电话",
            "email", "邮箱",
            "bankCard", "bank_card", "银行卡",
            "name", "username", "姓名"
    ));

    @Override
    public String parseAndMask(String logContent, RegexMaskEngine maskEngine) {
        if (logContent == null || logContent.isEmpty()) {
            return logContent;
        }
        try {
            JsonNode rootNode = objectMapper.readTree(logContent);
            maskJsonNodeRecursive(rootNode, "", maskEngine);
            return objectMapper.writeValueAsString(rootNode);
        } catch (Exception e) {
            return maskEngine.mask(logContent);
        }
    }

    private void maskJsonNodeRecursive(JsonNode node, String path, RegexMaskEngine maskEngine) {
        if (node == null || node.isNull()) {
            return;
        }

        if (node.isObject()) {
            maskObjectNode((ObjectNode) node, path, maskEngine);
        } else if (node.isArray()) {
            maskArrayNode((ArrayNode) node, path, maskEngine);
        } else if (node.isTextual()) {
            maskTextNode(node, path, maskEngine);
        } else if (node.isValueNode()) {
            maskValueNode(node, path, maskEngine);
        }
    }

    private void maskObjectNode(ObjectNode objectNode, String path, RegexMaskEngine maskEngine) {
        Iterator<Map.Entry<String, JsonNode>> fields = objectNode.fields();
        List<Map.Entry<String, JsonNode>> fieldList = new ArrayList<>();
        while (fields.hasNext()) {
            fieldList.add(fields.next());
        }

        for (Map.Entry<String, JsonNode> entry : fieldList) {
            String fieldName = entry.getKey();
            JsonNode valueNode = entry.getValue();
            String currentPath = path.isEmpty() ? fieldName : path + "." + fieldName;

            if (isSensitiveField(fieldName) || isSensitivePath(currentPath)) {
                if (valueNode.isTextual()) {
                    String fieldValue = valueNode.asText();
                    String maskedValue = maskEngine.mask(fieldValue);
                    if (!maskedValue.equals(fieldValue)) {
                        objectNode.put(fieldName, maskedValue);
                    }
                } else if (valueNode.isNumber()) {
                    String fieldValue = valueNode.asText();
                    String maskedValue = maskEngine.mask(fieldValue);
                    if (!maskedValue.equals(fieldValue)) {
                        try {
                            objectNode.put(fieldName, Long.parseLong(maskedValue));
                        } catch (NumberFormatException e) {
                            objectNode.put(fieldName, maskedValue);
                        }
                    }
                } else {
                    maskJsonNodeRecursive(valueNode, currentPath, maskEngine);
                }
            } else {
                maskJsonNodeRecursive(valueNode, currentPath, maskEngine);
            }
        }
    }

    private void maskArrayNode(ArrayNode arrayNode, String path, RegexMaskEngine maskEngine) {
        for (int i = 0; i < arrayNode.size(); i++) {
            JsonNode item = arrayNode.get(i);
            String currentPath = path + "[" + i + "]";

            if (item.isTextual()) {
                String original = item.asText();
                String masked = maskEngine.mask(original);
                if (!masked.equals(original)) {
                    arrayNode.set(i, TextNode.valueOf(masked));
                }
            } else if (item.isNumber()) {
                String original = item.asText();
                String masked = maskEngine.mask(original);
                if (!masked.equals(original)) {
                    try {
                        arrayNode.set(i, LongNode.valueOf(Long.parseLong(masked)));
                    } catch (NumberFormatException e) {
                        arrayNode.set(i, TextNode.valueOf(masked));
                    }
                }
            } else {
                maskJsonNodeRecursive(item, currentPath, maskEngine);
            }
        }
    }

    private void maskTextNode(JsonNode node, String path, RegexMaskEngine maskEngine) {
        String fieldValue = node.asText();
        String maskedValue = maskEngine.mask(fieldValue);
        if (!maskedValue.equals(fieldValue)) {
            if (node instanceof TextNode) {
                ((TextNode) node).setToken(maskedValue);
            }
        }
    }

    private void maskValueNode(JsonNode node, String path, RegexMaskEngine maskEngine) {
        String fieldValue = node.asText();
        String maskedValue = maskEngine.mask(fieldValue);
        if (!maskedValue.equals(fieldValue)) {
            if (node instanceof NumericNode) {
            }
        }
    }

    private boolean isSensitiveField(String fieldName) {
        String lowerName = fieldName.toLowerCase();
        for (String sensitive : sensitiveFields) {
            if (lowerName.contains(sensitive.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    private boolean isSensitivePath(String path) {
        String lowerPath = path.toLowerCase();
        for (String sensitive : sensitiveFields) {
            if (lowerPath.contains("." + sensitive.toLowerCase()) || 
                lowerPath.contains("[" + sensitive.toLowerCase() + "]")) {
                return true;
            }
        }
        return false;
    }

    public void addSensitiveField(String fieldName) {
        sensitiveFields.add(fieldName.toLowerCase());
    }

    public void removeSensitiveField(String fieldName) {
        sensitiveFields.remove(fieldName.toLowerCase());
    }

    @Override
    public boolean supportFormat(String format) {
        return "json".equalsIgnoreCase(format);
    }
}

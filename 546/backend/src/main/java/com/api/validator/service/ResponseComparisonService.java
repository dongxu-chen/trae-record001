package com.api.validator.service;

import com.api.validator.model.ComparisonResult;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class ResponseComparisonService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public ComparisonResult compare(String env1Name, String env2Name, String env1ResponseBody, String env2ResponseBody) {
        ComparisonResult result = new ComparisonResult();
        result.setEnv1Name(env1Name);
        result.setEnv2Name(env2Name);
        result.setHasDifferences(false);

        try {
            JsonNode env1Node = objectMapper.readTree(env1ResponseBody);
            JsonNode env2Node = objectMapper.readTree(env2ResponseBody);

            compareJsonNodes(env1Node, env2Node, "", result);

        } catch (Exception e) {
            result.addDifference(new ComparisonResult.Difference(
                    "",
                    ComparisonResult.DifferenceType.STRUCTURE_MISMATCH,
                    env1ResponseBody,
                    env2ResponseBody,
                    "解析错误: " + e.getMessage()
            ));
        }

        result.sortDifferencesBySeverity();
        return result;
    }

    private void compareJsonNodes(JsonNode node1, JsonNode node2, String path, ComparisonResult result) {
        String currentPath = path.isEmpty() ? "root" : path;

        if (node1 == null && node2 == null) {
            return;
        }

        if (node1 == null || node1.isNull()) {
            result.addDifference(new ComparisonResult.Difference(
                    currentPath,
                    ComparisonResult.DifferenceType.FIELD_ADDED,
                    null,
                    getNodeValue(node2),
                    "字段在 " + result.getEnv2Name() + " 中存在，在 " + result.getEnv1Name() + " 中不存在"
            ));
            return;
        }

        if (node2 == null || node2.isNull()) {
            result.addDifference(new ComparisonResult.Difference(
                    currentPath,
                    ComparisonResult.DifferenceType.FIELD_REMOVED,
                    getNodeValue(node1),
                    null,
                    "字段在 " + result.getEnv1Name() + " 中存在，在 " + result.getEnv2Name() + " 中不存在"
            ));
            return;
        }

        if (node1.getNodeType() != node2.getNodeType()) {
            result.addDifference(new ComparisonResult.Difference(
                    currentPath,
                    ComparisonResult.DifferenceType.TYPE_CHANGED,
                    getNodeValue(node1),
                    getNodeValue(node2),
                    "类型变化: " + node1.getNodeType() + " -> " + node2.getNodeType()
            ));
            return;
        }

        if (node1.isObject()) {
            compareObjects(node1, node2, path, result);
        } else if (node1.isArray()) {
            compareArrays(node1, node2, path, result);
        } else {
            compareValues(node1, node2, currentPath, result);
        }
    }

    private void compareObjects(JsonNode obj1, JsonNode obj2, String path, ComparisonResult result) {
        Set<String> allFields = new HashSet<>();
        obj1.fieldNames().forEachRemaining(allFields::add);
        obj2.fieldNames().forEachRemaining(allFields::add);

        for (String field : allFields) {
            String fieldPath = path.isEmpty() ? field : path + "." + field;
            compareJsonNodes(obj1.get(field), obj2.get(field), fieldPath, result);
        }
    }

    private void compareArrays(JsonNode arr1, JsonNode arr2, String path, ComparisonResult result) {
        int len1 = arr1.size();
        int len2 = arr2.size();

        if (len1 != len2) {
            result.addDifference(new ComparisonResult.Difference(
                    path.isEmpty() ? "root" : path,
                    ComparisonResult.DifferenceType.ARRAY_LENGTH_CHANGED,
                    len1,
                    len2,
                    "数组长度变化: " + len1 + " -> " + len2
            ));
        }

        int minLen = Math.min(len1, len2);
        for (int i = 0; i < minLen; i++) {
            String itemPath = (path.isEmpty() ? "root" : path) + "[" + i + "]";
            compareJsonNodes(arr1.get(i), arr2.get(i), itemPath, result);
        }

        if (len1 > len2) {
            for (int i = len2; i < len1; i++) {
                String itemPath = (path.isEmpty() ? "root" : path) + "[" + i + "]";
                result.addDifference(new ComparisonResult.Difference(
                        itemPath,
                        ComparisonResult.DifferenceType.FIELD_REMOVED,
                        getNodeValue(arr1.get(i)),
                        null,
                        "数组元素在 " + result.getEnv2Name() + " 中不存在"
                ));
            }
        } else if (len2 > len1) {
            for (int i = len1; i < len2; i++) {
                String itemPath = (path.isEmpty() ? "root" : path) + "[" + i + "]";
                result.addDifference(new ComparisonResult.Difference(
                        itemPath,
                        ComparisonResult.DifferenceType.FIELD_ADDED,
                        null,
                        getNodeValue(arr2.get(i)),
                        "数组元素在 " + result.getEnv1Name() + " 中不存在"
                ));
            }
        }
    }

    private void compareValues(JsonNode val1, JsonNode val2, String path, ComparisonResult result) {
        if (!val1.equals(val2)) {
            result.addDifference(new ComparisonResult.Difference(
                    path,
                    ComparisonResult.DifferenceType.VALUE_CHANGED,
                    getNodeValue(val1),
                    getNodeValue(val2),
                    "值变化"
            ));
        }
    }

    private Object getNodeValue(JsonNode node) {
        if (node == null || node.isNull()) {
            return null;
        }
        if (node.isTextual()) {
            return node.asText();
        }
        if (node.isInt() || node.isLong()) {
            return node.asLong();
        }
        if (node.isDouble() || node.isFloat()) {
            return node.asDouble();
        }
        if (node.isBoolean()) {
            return node.asBoolean();
        }
        if (node.isObject()) {
            try {
                return objectMapper.treeToValue(node, Map.class);
            } catch (Exception e) {
                return node.toString();
            }
        }
        if (node.isArray()) {
            try {
                return objectMapper.treeToValue(node, List.class);
            } catch (Exception e) {
                return node.toString();
            }
        }
        return node.toString();
    }

    public Map<String, Object> generateComparisonReport(ComparisonResult result) {
        Map<String, Object> report = new LinkedHashMap<>();

        report.put("env1Name", result.getEnv1Name());
        report.put("env2Name", result.getEnv2Name());
        report.put("path", result.getPath());
        report.put("method", result.getMethod());
        report.put("hasDifferences", result.isHasDifferences());
        report.put("totalDifferences", result.getDifferences().size());

        Map<String, Integer> differenceTypeCount = new LinkedHashMap<>();
        Map<String, Integer> severityCount = new LinkedHashMap<>();
        for (ComparisonResult.Difference diff : result.getDifferences()) {
            String type = diff.getType().name();
            differenceTypeCount.put(type, differenceTypeCount.getOrDefault(type, 0) + 1);
            
            String severity = diff.getSeverity() != null ? diff.getSeverity().name() : "LOW";
            severityCount.put(severity, severityCount.getOrDefault(severity, 0) + 1);
        }
        report.put("differenceTypeSummary", differenceTypeCount);
        report.put("severitySummary", severityCount);

        List<Map<String, Object>> categorizedDifferences = new ArrayList<>();
        for (ComparisonResult.Difference diff : result.getDifferences()) {
            Map<String, Object> diffMap = new LinkedHashMap<>();
            diffMap.put("field", diff.getField());
            diffMap.put("type", diff.getType().name());
            diffMap.put("severity", diff.getSeverity() != null ? diff.getSeverity().name() : "LOW");
            diffMap.put("env1Value", diff.getEnv1Value());
            diffMap.put("env2Value", diff.getEnv2Value());
            diffMap.put("description", diff.getDescription());
            categorizedDifferences.add(diffMap);
        }
        report.put("differences", categorizedDifferences);

        if (result.getEnv1Validation() != null) {
            report.put("env1Validation", result.getEnv1Validation());
        }
        if (result.getEnv2Validation() != null) {
            report.put("env2Validation", result.getEnv2Validation());
        }

        return report;
    }
}

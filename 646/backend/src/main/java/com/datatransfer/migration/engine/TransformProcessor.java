package com.datatransfer.migration.engine;

import java.util.List;
import java.util.Map;

public class TransformProcessor implements DataProcessor {
    private final List<Map<String, Object>> transformRules;

    public TransformProcessor(List<Map<String, Object>> transformRules) {
        this.transformRules = transformRules;
    }

    @Override
    public void process(Record record) throws Exception {
        if (transformRules == null || transformRules.isEmpty()) return;
        applyTransform(record);
    }

    @Override
    public void processBatch(List<Record> records) throws Exception {
        if (transformRules == null || transformRules.isEmpty()) return;
        for (Record record : records) {
            applyTransform(record);
        }
    }

    private void applyTransform(Record record) {
        for (Map<String, Object> rule : transformRules) {
            String sourceField = (String) rule.get("sourceField");
            String targetField = (String) rule.get("targetField");
            String transformType = (String) rule.get("transformType");

            if (record.containsKey(sourceField)) {
                Object value = record.get(sourceField);
                Object transformedValue = transform(value, transformType, rule);
                if (targetField != null && !targetField.isEmpty()) {
                    record.set(targetField, transformedValue);
                    if (!sourceField.equals(targetField)) {
                        record.remove(sourceField);
                    }
                } else {
                    record.set(sourceField, transformedValue);
                }
            }
        }
    }

    private Object transform(Object value, String transformType, Map<String, Object> rule) {
        if (value == null) return null;
        switch (transformType != null ? transformType.toLowerCase() : "") {
            case "uppercase": return value.toString().toUpperCase();
            case "lowercase": return value.toString().toLowerCase();
            case "trim": return value.toString().trim();
            case "substring":
                String strValue = value.toString();
                int start = rule.get("start") != null ? ((Number) rule.get("start")).intValue() : 0;
                int end = rule.get("end") != null ? ((Number) rule.get("end")).intValue() : strValue.length();
                return strValue.substring(start, Math.min(end, strValue.length()));
            case "tostring": return value.toString();
            default: return value;
        }
    }
}

package com.datasecurity.masking.label;

import com.datasecurity.masking.enums.SensitiveType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class LabelPropagationEngine {

    private final Map<String, FieldLabel> fieldLabelRegistry = new ConcurrentHashMap<>();

    public FieldLabel createFieldLabel(String tableName, String columnName,
                                    SensitiveType sensitiveType, SensitivityLevel level) {
        String key = tableName + "." + columnName;
        FieldLabel label = new FieldLabel(tableName, columnName, sensitiveType, level);
        fieldLabelRegistry.put(key, label);
        log.debug("Created field label: {}", key);
        return label;
    }

    public FieldLabel getFieldLabel(String tableName, String columnName) {
        String key = tableName + "." + columnName;
        return fieldLabelRegistry.get(key);
    }

    public FieldLabel getFieldLabel(String fullColumnName) {
        return fieldLabelRegistry.get(fullColumnName);
    }

    public void propagateLabel(String sourceField, String targetField) {
        FieldLabel source = fieldLabelRegistry.get(sourceField);
        if (sourceLabel == null) {
            log.warn("Source field label not found: {}", sourceField);
            return;
        }

        sourceLabel.addDownstreamField(targetField);

        if (!fieldLabelRegistry.containsKey(targetField)) {
            FieldLabel targetLabel = fieldLabelRegistry.get(targetField);
            if (sourceLabel.getSensitivityLevel().isMoreSensitiveThan(targetLabel.getSensitivityLevel())) {
                targetLabel.setSensitivityLevel(sourceLabel.getSensitivityLevel());
                log.info("Propagated sensitivity level from {} to {}", sourceField, targetField);
            }
        } else {
            FieldLabel newLabel = new FieldLabel(
                    extractTableName(targetField),
                    extractColumnName(targetField),
                    sourceLabel.getSensitiveType(),
                    sourceLabel.getSensitivityLevel()
            );
            newLabel.setSource("propagated_from:" + sourceField);
            fieldLabelRegistry.put(targetField, newLabel);
            log.info("Propagated label from {} to new field {}", sourceField, targetField);
        }
    }

    public void propagateLabels(List<String> sourceFields, String targetField) {
        SensitivityLevel maxLevel = SensitivityLevel.PUBLIC;
        SensitiveType sensitiveType = null;

        for (String sourceField : sourceFields) {
            FieldLabel sourceLabel = fieldLabelRegistry.get(sourceField);
            if (sourceLabel != null) {
                if (sourceLabel.getSensitivityLevel().isMoreSensitiveThan(maxLevel)) {
                    maxLevel = sourceLabel.getSensitivityLevel();
                }
                if (sensitiveType == null) {
                    sensitiveType = sourceLabel.getSensitiveType();
                }
            }
        }

        String tableName = extractTableName(targetField);
        String columnName = extractColumnName(targetField);
        createFieldLabel(tableName, columnName, sensitiveType, maxLevel);
        log.info("Propagated combined label from {} fields to {} with level {}",
                sourceFields.size(), targetField, maxLevel);
    }

    public SensitivityLevel calculateDataSetLevel(List<FieldLabel> fields) {
        if (fields == null || fields.isEmpty()) {
            return SensitivityLevel.PUBLIC;
        }

        SensitivityLevel maxLevel = SensitivityLevel.PUBLIC;
        for (FieldLabel field : fields) {
            if (field.getSensitivityLevel().isMoreSensitiveThan(maxLevel)) {
                maxLevel = field.getSensitivityLevel();
            }
        }
        return maxLevel;
    }

    public SensitivityLevel calculateResultSetLevel(List<Map<String, Object>> resultSet,
                                                List<String> tableNames) {
        if (resultSet == null || resultSet.isEmpty()) {
            return SensitivityLevel.PUBLIC;
        }

        SensitivityLevel maxLevel = SensitivityLevel.PUBLIC;

        if (tableNames != null) {
            for (String tableName : tableNames) {
                for (String columnName : resultSet.get(0).keySet()) {
                    FieldLabel label = getFieldLabel(tableName, columnName);
                    if (label != null) {
                        if (label.getSensitivityLevel().isMoreSensitiveThan(maxLevel)) {
                            maxLevel = label.getSensitivityLevel();
                        }
                    }
                }
            }
        }

        return maxLevel;
    }

    private String extractTableName(String fullColumnName) {
        int dotIndex = fullColumnName.indexOf('.');
        if (dotIndex > 0) {
            return fullColumnName.substring(0, dotIndex);
        }
        return "unknown";
    }

    private String extractColumnName(String fullColumnName) {
        int dotIndex = fullColumnName.indexOf('.');
        if (dotIndex > 0) {
            return fullColumnName.substring(dotIndex + 1);
        }
        return fullColumnName;
    }

    public Map<String, FieldLabel> getAllFieldLabels() {
        return new ConcurrentHashMap<>(fieldLabelRegistry);
    }

    public void removeFieldLabel(String fullColumnName) {
        fieldLabelRegistry.remove(fullColumnName);
    }

    public void clearAllLabels() {
        fieldLabelRegistry.clear();
        log.info("Cleared all field labels");
    }
}

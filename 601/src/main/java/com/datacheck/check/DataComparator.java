package com.datacheck.check;

import com.datacheck.config.ThresholdConfig;
import com.datacheck.model.CheckTask;
import com.datacheck.model.DataRecord;
import com.datacheck.model.DiffResult;
import com.datacheck.model.enums.DiffType;
import com.datacheck.model.enums.RepairStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Component
public class DataComparator {

    private final ThresholdConfig thresholdConfig;

    @Autowired
    public DataComparator(ThresholdConfig thresholdConfig) {
        this.thresholdConfig = thresholdConfig;
    }

    public Optional<DiffResult> compare(DataRecord sourceRecord, DataRecord targetRecord, CheckTask task) {
        if (sourceRecord == null && targetRecord == null) {
            return Optional.empty();
        }

        if (sourceRecord != null && targetRecord == null) {
            return Optional.of(buildDiffResult(sourceRecord, null, DiffType.MISSING_IN_TARGET,
                    null, 0, task));
        }

        if (sourceRecord == null && targetRecord != null) {
            return Optional.of(buildDiffResult(null, targetRecord, DiffType.MISSING_IN_SOURCE,
                    null, 0, task));
        }

        long latency = Math.abs(sourceRecord.getTimestamp() - targetRecord.getTimestamp());
        long latencyThreshold = thresholdConfig.getEffectiveLatencyThresholdMs(task);

        Map<String, Object> diffFields = compareFields(sourceRecord.getData(), targetRecord.getData(), task);

        if (!diffFields.isEmpty()) {
            return Optional.of(buildDiffResult(sourceRecord, targetRecord, DiffType.VALUE_MISMATCH,
                    diffFields, latency, task));
        }

        if (latency > latencyThreshold) {
            return Optional.of(buildDiffResult(sourceRecord, targetRecord, DiffType.LATENCY_EXCEEDED,
                    null, latency, task));
        }

        return Optional.empty();
    }

    private Map<String, Object> compareFields(Map<String, Object> sourceData,
                                              Map<String, Object> targetData,
                                              CheckTask task) {
        Map<String, Object> diffFields = new LinkedHashMap<>();
        Set<String> fieldsToCompare = getFieldsToCompare(sourceData, targetData, task);
        Set<String> excludeFields = task.getExcludeFields() != null ?
                new HashSet<>(task.getExcludeFields()) : Collections.emptySet();

        for (String field : fieldsToCompare) {
            if (excludeFields.contains(field)) {
                continue;
            }
            Object sourceValue = sourceData.get(field);
            Object targetValue = targetData.get(field);

            if (!valuesEqual(sourceValue, targetValue)) {
                Map<String, Object> diffDetail = new LinkedHashMap<>();
                diffDetail.put("source", sourceValue);
                diffDetail.put("target", targetValue);
                diffFields.put(field, diffDetail);
            }
        }

        return diffFields;
    }

    private Set<String> getFieldsToCompare(Map<String, Object> sourceData,
                                           Map<String, Object> targetData,
                                           CheckTask task) {
        if (task.getCompareFields() != null && !task.getCompareFields().isEmpty()) {
            return new LinkedHashSet<>(task.getCompareFields());
        }
        Set<String> fields = new LinkedHashSet<>(sourceData.keySet());
        fields.addAll(targetData.keySet());
        return fields;
    }

    private boolean valuesEqual(Object value1, Object value2) {
        if (value1 == value2) {
            return true;
        }
        if (value1 == null || value2 == null) {
            return false;
        }
        if (value1 instanceof Number && value2 instanceof Number) {
            return ((Number) value1).doubleValue() == ((Number) value2).doubleValue();
        }
        if (value1 instanceof byte[] && value2 instanceof byte[]) {
            return Arrays.equals((byte[]) value1, (byte[]) value2);
        }
        if (value1 instanceof Map && value2 instanceof Map) {
            return compareMaps((Map<?, ?>) value1, (Map<?, ?>) value2);
        }
        if (value1 instanceof Collection && value2 instanceof Collection) {
            return compareCollections((Collection<?>) value1, (Collection<?>) value2);
        }
        return value1.equals(value2) || value1.toString().equals(value2.toString());
    }

    private boolean compareMaps(Map<?, ?> map1, Map<?, ?> map2) {
        if (map1.size() != map2.size()) {
            return false;
        }
        for (Map.Entry<?, ?> entry : map1.entrySet()) {
            Object key = entry.getKey();
            if (!map2.containsKey(key)) {
                return false;
            }
            if (!valuesEqual(entry.getValue(), map2.get(key))) {
                return false;
            }
        }
        return true;
    }

    private boolean compareCollections(Collection<?> col1, Collection<?> col2) {
        if (col1.size() != col2.size()) {
            return false;
        }
        List<?> list1 = new ArrayList<>(col1);
        List<?> list2 = new ArrayList<>(col2);
        for (int i = 0; i < list1.size(); i++) {
            if (!valuesEqual(list1.get(i), list2.get(i))) {
                return false;
            }
        }
        return true;
    }

    private DiffResult buildDiffResult(DataRecord sourceRecord, DataRecord targetRecord,
                                       DiffType diffType, Map<String, Object> diffFields,
                                       long latencyMs, CheckTask task) {
        String key = sourceRecord != null ? sourceRecord.getKey() :
                (targetRecord != null ? targetRecord.getKey() : null);

        return DiffResult.builder()
                .id(UUID.randomUUID().toString())
                .key(key)
                .diffType(diffType)
                .sourceType(task.getSourceType())
                .tableName(task.getTableName())
                .sourceData(sourceRecord != null ? sourceRecord.getData() : null)
                .targetData(targetRecord != null ? targetRecord.getData() : null)
                .diffFields(diffFields)
                .latencyMs(latencyMs)
                .detectedAt(LocalDateTime.now())
                .repairStatus(RepairStatus.PENDING)
                .repairAttempts(0)
                .build();
    }
}

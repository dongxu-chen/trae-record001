package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ConflictResolutionService {

    private final DataMappingService dataMappingService;

    public ConflictResolutionService(DataMappingService dataMappingService) {
        this.dataMappingService = dataMappingService;
    }

    public List<RowData> resolveConflicts(List<RowData> rowDataList, SyncConfig.TableMapping tableMapping) {
        if (rowDataList == null || rowDataList.isEmpty()) {
            return Collections.emptyList();
        }

        List<RowData> insertOrUpdateRows = new ArrayList<>();
        List<RowData> deleteRows = new ArrayList<>();

        for (RowData rowData : rowDataList) {
            if (rowData.getEventType() == RowData.EventType.DELETE) {
                deleteRows.add(rowData);
            } else {
                insertOrUpdateRows.add(rowData);
            }
        }

        Map<String, RowData> mergedMap = mergeRowData(insertOrUpdateRows, tableMapping);
        List<RowData> result = new ArrayList<>(mergedMap.values());

        result.addAll(deleteRows);

        result.sort(Comparator.comparingLong(RowData::getTimestamp));

        return result;
    }

    private Map<String, RowData> mergeRowData(List<RowData> rowDataList, SyncConfig.TableMapping tableMapping) {
        Map<String, RowData> mergedMap = new LinkedHashMap<>();

        for (RowData rowData : rowDataList) {
            String key = buildPrimaryKey(rowData, tableMapping);

            if (key == null) {
                mergedMap.put(UUID.randomUUID().toString(), rowData);
                continue;
            }

            if (!mergedMap.containsKey(key)) {
                mergedMap.put(key, rowData);
            } else {
                RowData existing = mergedMap.get(key);
                RowData merged = mergeTwoRows(existing, rowData, tableMapping);
                mergedMap.put(key, merged);
            }
        }

        return mergedMap;
    }

    private RowData mergeTwoRows(RowData older, RowData newer, SyncConfig.TableMapping tableMapping) {
        SyncConfig.ConflictStrategy strategy = tableMapping.getConflictStrategy();

        switch (strategy) {
            case UPDATE:
                return newer;
            case IGNORE:
                return older;
            case THROW:
                throw new RuntimeException("Conflict detected for table " +
                        tableMapping.getTargetTable() + " with keys: " +
                        buildPrimaryKey(newer, tableMapping));
            case VERSION:
                return resolveByVersion(older, newer);
            default:
                return newer;
        }
    }

    private RowData resolveByVersion(RowData older, RowData newer) {
        if (newer.getTimestamp() >= older.getTimestamp()) {
            return newer;
        }
        return older;
    }

    private String buildPrimaryKey(RowData rowData, SyncConfig.TableMapping tableMapping) {
        List<String> primaryKeys = tableMapping.getPrimaryKeys();
        if (primaryKeys == null || primaryKeys.isEmpty()) {
            return null;
        }

        Map<String, Object> data = rowData.getCurrentData();
        if (data == null) {
            return null;
        }

        List<String> keyValues = new ArrayList<>();
        for (String pk : primaryKeys) {
            String sourceColumn = findSourceColumn(pk, tableMapping);
            Object value = data.get(sourceColumn);
            if (value == null) {
                return null;
            }
            keyValues.add(value.toString());
        }

        return String.join("_", keyValues);
    }

    private String findSourceColumn(String targetColumn, SyncConfig.TableMapping tableMapping) {
        if (tableMapping.getColumnMapping() == null || tableMapping.getColumnMapping().isEmpty()) {
            return targetColumn;
        }

        for (SyncConfig.ColumnMapping cm : tableMapping.getColumnMapping()) {
            if (cm.getTarget().equals(targetColumn)) {
                return cm.getSource();
            }
        }

        return targetColumn;
    }

    public Map<String, Object> extractPrimaryKeyValues(RowData rowData, SyncConfig.TableMapping tableMapping) {
        Map<String, Object> pkValues = new LinkedHashMap<>();
        List<String> primaryKeys = tableMapping.getPrimaryKeys();

        if (primaryKeys == null || primaryKeys.isEmpty()) {
            return pkValues;
        }

        Map<String, Object> mappedData = dataMappingService.mapRowData(rowData, tableMapping);

        for (String pk : primaryKeys) {
            pkValues.put(pk, mappedData.get(pk));
        }

        return pkValues;
    }

    public boolean needsDeleteHandling(RowData rowData) {
        return rowData.getEventType() == RowData.EventType.DELETE;
    }

    public List<RowData> filterValidRows(List<RowData> rowDataList, SyncConfig.TableMapping tableMapping) {
        return rowDataList.stream()
                .filter(r -> isRowValid(r, tableMapping))
                .collect(Collectors.toList());
    }

    private boolean isRowValid(RowData rowData, SyncConfig.TableMapping tableMapping) {
        if (rowData == null || rowData.getCurrentData() == null) {
            return false;
        }

        if (tableMapping.getPrimaryKeys() == null || tableMapping.getPrimaryKeys().isEmpty()) {
            return true;
        }

        Map<String, Object> data = rowData.getCurrentData();
        for (String pk : tableMapping.getPrimaryKeys()) {
            String sourceColumn = findSourceColumn(pk, tableMapping);
            if (data.get(sourceColumn) == null) {
                log.warn("Row has null primary key value for column: {}", sourceColumn);
                return false;
            }
        }

        return true;
    }
}

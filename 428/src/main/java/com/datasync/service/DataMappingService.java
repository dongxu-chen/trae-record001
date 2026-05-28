package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import com.datasync.transform.ExpressionEngine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class DataMappingService {

    private final SyncConfig syncConfig;
    private final ExpressionEngine expressionEngine;

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter DATETIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public DataMappingService(SyncConfig syncConfig, ExpressionEngine expressionEngine) {
        this.syncConfig = syncConfig;
        this.expressionEngine = expressionEngine;
    }

    public SyncConfig.TableMapping getTableMapping(String database, String table) {
        return syncConfig.getTables().stream()
                .filter(t -> t.getSourceSchema().equals(database) && t.getSourceTable().equals(table))
                .findFirst()
                .orElse(null);
    }

    public List<SyncConfig.ColumnMapping> getEffectiveColumnMappings(SyncConfig.TableMapping tableMapping, RowData rowData) {
        if (tableMapping.getColumnMapping() != null && !tableMapping.getColumnMapping().isEmpty()) {
            return tableMapping.getColumnMapping();
        }

        return autoDiscoverColumnMappings(rowData);
    }

    private List<SyncConfig.ColumnMapping> autoDiscoverColumnMappings(RowData rowData) {
        Map<String, Object> data = rowData.getCurrentData();
        if (data == null || data.isEmpty()) {
            return Collections.emptyList();
        }

        List<SyncConfig.ColumnMapping> mappings = new ArrayList<>();
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            SyncConfig.ColumnMapping cm = new SyncConfig.ColumnMapping();
            cm.setSource(entry.getKey());
            cm.setTarget(entry.getKey());
            cm.setType(inferClickHouseType(entry.getValue()));
            mappings.add(cm);
        }
        return mappings;
    }

    private String inferClickHouseType(Object value) {
        if (value == null) {
            return "String";
        }

        if (value instanceof Integer || value instanceof Long) {
            return "Int64";
        } else if (value instanceof Float || value instanceof Double) {
            return "Float64";
        } else if (value instanceof Boolean) {
            return "UInt8";
        } else if (value instanceof java.math.BigDecimal) {
            return "Decimal(18,4)";
        } else if (value instanceof LocalDate) {
            return "Date";
        } else if (value instanceof LocalDateTime || value instanceof java.util.Date) {
            return "DateTime";
        } else {
            return "String";
        }
    }

    public Map<String, Object> mapRowData(RowData rowData, SyncConfig.TableMapping tableMapping) {
        Map<String, Object> result = new LinkedHashMap<>();
        Map<String, Object> sourceData = rowData.getCurrentData();

        if (sourceData == null) {
            return result;
        }

        List<SyncConfig.ColumnMapping> columnMappings = getEffectiveColumnMappings(tableMapping, rowData);

        for (SyncConfig.ColumnMapping cm : columnMappings) {
            Object value = sourceData.get(cm.getSource());

            if (value == null && cm.getDefaultValue() != null) {
                value = cm.getDefaultValue();
            }

            if (cm.getExpression() != null && !cm.getExpression().isEmpty()) {
                value = evaluateExpression(cm.getExpression(), sourceData);
            }

            value = convertDataType(value, cm.getType());
            result.put(cm.getTarget(), value);
        }

        return result;
    }

    private Object evaluateExpression(String expression, Map<String, Object> sourceData) {
        return expressionEngine.evaluate(expression, sourceData);
    }

    public Object convertDataType(Object value, String targetType) {
        if (value == null) {
            return null;
        }

        String typeLower = targetType.toLowerCase();

        try {
            if (typeLower.contains("int") || typeLower.contains("uint")) {
                if (value instanceof Number) {
                    return ((Number) value).longValue();
                }
                return Long.parseLong(value.toString());
            } else if (typeLower.contains("float") || typeLower.contains("double")) {
                if (value instanceof Number) {
                    return ((Number) value).doubleValue();
                }
                return Double.parseDouble(value.toString());
            } else if (typeLower.contains("decimal")) {
                if (value instanceof java.math.BigDecimal) {
                    return value;
                }
                return new java.math.BigDecimal(value.toString());
            } else if (typeLower.contains("bool")) {
                if (value instanceof Boolean) {
                    return value;
                }
                return Boolean.parseBoolean(value.toString());
            } else if (typeLower.equals("date")) {
                return convertToDate(value);
            } else if (typeLower.equals("datetime")) {
                return convertToDateTime(value);
            } else {
                return value.toString();
            }
        } catch (Exception e) {
            log.warn("Failed to convert value {} to type {}, returning original value", value, targetType);
            return value.toString();
        }
    }

    private String convertToDate(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof java.sql.Date) {
            return ((java.sql.Date) value).toLocalDate().format(DATE_FORMATTER);
        } else if (value instanceof LocalDate) {
            return ((LocalDate) value).format(DATE_FORMATTER);
        } else if (value instanceof LocalDateTime) {
            return ((LocalDateTime) value).toLocalDate().format(DATE_FORMATTER);
        } else if (value instanceof java.util.Date) {
            return new java.sql.Date(((java.util.Date) value).getTime())
                    .toLocalDate().format(DATE_FORMATTER);
        } else {
            return value.toString();
        }
    }

    private String convertToDateTime(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof java.sql.Timestamp) {
            return ((java.sql.Timestamp) value).toLocalDateTime().format(DATETIME_FORMATTER);
        } else if (value instanceof LocalDateTime) {
            return ((LocalDateTime) value).format(DATETIME_FORMATTER);
        } else if (value instanceof java.util.Date) {
            return new java.sql.Timestamp(((java.util.Date) value).getTime())
                    .toLocalDateTime().format(DATETIME_FORMATTER);
        } else {
            return value.toString();
        }
    }

    public Map<String, String> getColumnTypeMap(RowData rowData) {
        Map<String, String> typeMap = new HashMap<>();
        if (rowData.getColumns() != null) {
            for (Map.Entry<String, RowData.ColumnInfo> entry : rowData.getColumns().entrySet()) {
                String mysqlType = entry.getValue().getMysqlType();
                typeMap.put(entry.getKey(), convertMysqlToClickHouseType(mysqlType));
            }
        }
        return typeMap;
    }

    private String convertMysqlToClickHouseType(String mysqlType) {
        String typeLower = mysqlType.toLowerCase();

        if (typeLower.contains("tinyint") || typeLower.contains("bool")) {
            return "UInt8";
        } else if (typeLower.contains("smallint")) {
            return "Int16";
        } else if (typeLower.contains("mediumint")) {
            return "Int32";
        } else if (typeLower.contains("bigint")) {
            return "Int64";
        } else if (typeLower.contains("int")) {
            return "Int32";
        } else if (typeLower.contains("float")) {
            return "Float32";
        } else if (typeLower.contains("double") || typeLower.contains("real")) {
            return "Float64";
        } else if (typeLower.contains("decimal") || typeLower.contains("numeric")) {
            return "Decimal(18,4)";
        } else if (typeLower.contains("datetime") || typeLower.contains("timestamp")) {
            return "DateTime";
        } else if (typeLower.contains("date")) {
            return "Date";
        } else if (typeLower.contains("json")) {
            return "String";
        } else if (typeLower.contains("blob") || typeLower.contains("binary")) {
            return "String";
        } else {
            return "String";
        }
    }
}

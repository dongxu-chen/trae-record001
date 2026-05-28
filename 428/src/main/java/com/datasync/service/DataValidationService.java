package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.ValidationResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class DataValidationService {

    private final JdbcTemplate mysqlJdbcTemplate;
    private final JdbcTemplate clickHouseJdbcTemplate;
    private final SyncConfig syncConfig;
    private final DataMappingService dataMappingService;

    private final ExecutorService validationExecutor = Executors.newFixedThreadPool(2);
    private final Map<String, ValidationResult> lastValidationResults = new ConcurrentHashMap<>();
    private final Map<String, Long> validationTimestamps = new ConcurrentHashMap<>();

    @Autowired
    public DataValidationService(@Qualifier("mysqlJdbcTemplate") JdbcTemplate mysqlJdbcTemplate,
                                 @Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate,
                                 SyncConfig syncConfig,
                                 DataMappingService dataMappingService) {
        this.mysqlJdbcTemplate = mysqlJdbcTemplate;
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
        this.syncConfig = syncConfig;
        this.dataMappingService = dataMappingService;
    }

    @Scheduled(cron = "0 0 2 * * ?")
    public void scheduledValidation() {
        log.info("Starting scheduled data validation");
        validateAllTables();
    }

    public List<ValidationResult> validateAllTables() {
        List<ValidationResult> results = new ArrayList<>();

        for (SyncConfig.TableMapping tableMapping : syncConfig.getTables()) {
            try {
                ValidationResult result = validateTable(tableMapping);
                results.add(result);
                lastValidationResults.put(getTableKey(tableMapping), result);
                validationTimestamps.put(getTableKey(tableMapping), System.currentTimeMillis());
            } catch (Exception e) {
                log.error("Validation failed for table: {}.{}",
                        tableMapping.getSourceSchema(), tableMapping.getSourceTable(), e);
            }
        }

        return results;
    }

    public ValidationResult validateTable(String schema, String table) {
        SyncConfig.TableMapping tableMapping = dataMappingService.getTableMapping(schema, table);
        if (tableMapping == null) {
            throw new IllegalArgumentException("No table mapping found for: " + schema + "." + table);
        }
        return validateTable(tableMapping);
    }

    public ValidationResult validateTable(SyncConfig.TableMapping tableMapping) {
        long startTime = System.currentTimeMillis();
        String sourceSchema = tableMapping.getSourceSchema();
        String sourceTable = tableMapping.getSourceTable();
        String targetDatabase = tableMapping.getTargetDatabase();
        String targetTable = tableMapping.getTargetTable();

        log.info("Starting validation for {}.{} -> {}.{}",
                sourceSchema, sourceTable, targetDatabase, targetTable);

        ValidationResult.ValidationResultBuilder resultBuilder = ValidationResult.builder()
                .sourceSchema(sourceSchema)
                .sourceTable(sourceTable)
                .targetDatabase(targetDatabase)
                .targetTable(targetTable)
                .validationTime(startTime);

        try {
            long sourceRowCount = getSourceRowCount(sourceSchema, sourceTable);
            long targetRowCount = getTargetRowCount(targetDatabase, targetTable);

            resultBuilder.sourceRowCount(sourceRowCount)
                    .targetRowCount(targetRowCount);

            if (sourceRowCount == 0 && targetRowCount == 0) {
                resultBuilder.status(ValidationResult.ValidationStatus.SUCCESS)
                        .matchCount(0)
                        .diffCount(0)
                        .durationMs(System.currentTimeMillis() - startTime);
                log.info("Validation completed for {}.{}: both tables empty", sourceSchema, sourceTable);
                return resultBuilder.build();
            }

            if (Math.abs(sourceRowCount - targetRowCount) > sourceRowCount * 0.01) {
                resultBuilder.status(ValidationResult.ValidationStatus.WARNING);
                log.warn("Row count mismatch for {}.{}: source={}, target={}",
                        sourceSchema, sourceTable, sourceRowCount, targetRowCount);
            }

            List<ValidationResult.RowDiff> diffs = compareRows(tableMapping);
            long matchCount = sourceRowCount - diffs.size();

            resultBuilder.rowDiffs(diffs)
                    .matchCount(matchCount)
                    .diffCount(diffs.size());

            if (diffs.isEmpty()) {
                resultBuilder.status(ValidationResult.ValidationStatus.SUCCESS);
            } else {
                resultBuilder.status(ValidationResult.ValidationStatus.FAILED);
            }

        } catch (Exception e) {
            log.error("Validation error for {}.{}", sourceSchema, sourceTable, e);
            resultBuilder.status(ValidationResult.ValidationStatus.ERROR)
                    .errorMessage(e.getMessage());
        }

        resultBuilder.durationMs(System.currentTimeMillis() - startTime);
        ValidationResult result = resultBuilder.build();

        log.info("Validation completed for {}.{}: status={}, matchRate={}%, duration={}ms",
                sourceSchema, sourceTable, result.getStatus(),
                String.format("%.2f", result.getMatchRate()),
                result.getDurationMs());

        return result;
    }

    private List<ValidationResult.RowDiff> compareRows(SyncConfig.TableMapping tableMapping) {
        List<ValidationResult.RowDiff> diffs = new ArrayList<>();

        String sourceSchema = tableMapping.getSourceSchema();
        String sourceTable = tableMapping.getSourceTable();
        String targetDatabase = tableMapping.getTargetDatabase();
        String targetTable = tableMapping.getTargetTable();

        List<String> primaryKeys = tableMapping.getPrimaryKeys();
        if (primaryKeys == null || primaryKeys.isEmpty()) {
            log.warn("No primary keys defined for {}.{}, skipping row comparison",
                    sourceSchema, sourceTable);
            return diffs;
        }

        List<SyncConfig.ColumnMapping> columnMappings = tableMapping.getColumnMapping();
        if (columnMappings == null || columnMappings.isEmpty()) {
            log.warn("No column mappings defined for {}.{}, skipping row comparison",
                    sourceSchema, sourceTable);
            return diffs;
        }

        int batchSize = 1000;
        long offset = 0;
        long maxDiffs = 100;

        while (diffs.size() < maxDiffs) {
            List<Map<String, Object>> sourceRows = fetchSourceRows(sourceSchema, sourceTable, offset, batchSize);
            if (sourceRows.isEmpty()) {
                break;
            }

            Set<String> sourceKeys = sourceRows.stream()
                    .map(row -> buildPrimaryKey(row, primaryKeys))
                    .collect(Collectors.toSet());

            List<Map<String, Object>> targetRows = fetchTargetRows(targetDatabase, targetTable, sourceKeys, tableMapping);
            Map<String, Map<String, Object>> targetRowMap = targetRows.stream()
                    .collect(Collectors.toMap(
                            row -> buildPrimaryKeyFromTarget(row, primaryKeys, tableMapping),
                            row -> row,
                            (r1, r2) -> r1
                    ));

            for (Map<String, Object> sourceRow : sourceRows) {
                String pk = buildPrimaryKey(sourceRow, primaryKeys);
                Map<String, Object> targetRow = targetRowMap.get(pk);

                if (targetRow == null) {
                    diffs.add(ValidationResult.RowDiff.builder()
                            .primaryKey(pk)
                            .diffType(ValidationResult.DiffType.SOURCE_ONLY)
                            .sourceRow(sourceRow)
                            .build());
                } else {
                    List<ValidationResult.ColumnDiff> columnDiffs = compareColumns(
                            sourceRow, targetRow, columnMappings);
                    if (!columnDiffs.isEmpty()) {
                        diffs.add(ValidationResult.RowDiff.builder()
                                .primaryKey(pk)
                                .diffType(ValidationResult.DiffType.VALUE_MISMATCH)
                                .sourceRow(sourceRow)
                                .targetRow(targetRow)
                                .columnDiffs(columnDiffs)
                                .build());
                    }
                }

                targetRowMap.remove(pk);
            }

            for (Map.Entry<String, Map<String, Object>> entry : targetRowMap.entrySet()) {
                diffs.add(ValidationResult.RowDiff.builder()
                        .primaryKey(entry.getKey())
                        .diffType(ValidationResult.DiffType.TARGET_ONLY)
                        .targetRow(entry.getValue())
                        .build());
            }

            offset += batchSize;
        }

        return diffs;
    }

    private List<ValidationResult.ColumnDiff> compareColumns(Map<String, Object> sourceRow,
                                                              Map<String, Object> targetRow,
                                                              List<SyncConfig.ColumnMapping> columnMappings) {
        List<ValidationResult.ColumnDiff> diffs = new ArrayList<>();

        for (SyncConfig.ColumnMapping cm : columnMappings) {
            Object sourceValue = sourceRow.get(cm.getSource());
            Object targetValue = targetRow.get(cm.getTarget());

            if (!valuesEqual(sourceValue, targetValue)) {
                diffs.add(ValidationResult.ColumnDiff.builder()
                        .columnName(cm.getTarget())
                        .sourceValue(sourceValue)
                        .targetValue(targetValue)
                        .sourceType(sourceValue != null ? sourceValue.getClass().getSimpleName() : "null")
                        .targetType(targetValue != null ? targetValue.getClass().getSimpleName() : "null")
                        .build());
            }
        }

        return diffs;
    }

    private boolean valuesEqual(Object source, Object target) {
        if (source == null && target == null) {
            return true;
        }
        if (source == null || target == null) {
            return false;
        }

        String sourceStr = source.toString().trim();
        String targetStr = target.toString().trim();

        return sourceStr.equals(targetStr);
    }

    private String buildPrimaryKey(Map<String, Object> row, List<String> primaryKeys) {
        return primaryKeys.stream()
                .map(pk -> {
                    Object value = row.get(pk);
                    return value != null ? value.toString() : "null";
                })
                .collect(Collectors.joining("|"));
    }

    private String buildPrimaryKeyFromTarget(Map<String, Object> row, List<String> primaryKeys,
                                             SyncConfig.TableMapping tableMapping) {
        return primaryKeys.stream()
                .map(pk -> {
                    String sourceColumn = getSourceColumn(pk, tableMapping);
                    Object value = row.get(sourceColumn);
                    return value != null ? value.toString() : "null";
                })
                .collect(Collectors.joining("|"));
    }

    private String getSourceColumn(String targetColumn, SyncConfig.TableMapping tableMapping) {
        if (tableMapping.getColumnMapping() == null) {
            return targetColumn;
        }
        for (SyncConfig.ColumnMapping cm : tableMapping.getColumnMapping()) {
            if (cm.getTarget().equals(targetColumn)) {
                return cm.getSource();
            }
        }
        return targetColumn;
    }

    private long getSourceRowCount(String schema, String table) {
        String sql = "SELECT COUNT(*) FROM " + schema + "." + table;
        return mysqlJdbcTemplate.queryForObject(sql, Long.class);
    }

    private long getTargetRowCount(String database, String table) {
        String sql = "SELECT COUNT(*) FROM " + database + "." + table;
        return clickHouseJdbcTemplate.queryForObject(sql, Long.class);
    }

    private List<Map<String, Object>> fetchSourceRows(String schema, String table, long offset, int limit) {
        String sql = "SELECT * FROM " + schema + "." + table + " LIMIT ?, ?";
        return mysqlJdbcTemplate.queryForList(sql, offset, limit);
    }

    private List<Map<String, Object>> fetchTargetRows(String database, String table,
                                                       Set<String> primaryKeys,
                                                       SyncConfig.TableMapping tableMapping) {
        if (primaryKeys.isEmpty()) {
            return Collections.emptyList();
        }

        List<String> targetPrimaryKeys = tableMapping.getPrimaryKeys();
        String whereClause = buildWhereClause(targetPrimaryKeys, primaryKeys, tableMapping);

        String sql = "SELECT * FROM " + database + "." + table + " WHERE " + whereClause;
        return clickHouseJdbcTemplate.queryForList(sql);
    }

    private String buildWhereClause(List<String> primaryKeys, Set<String> keyValues,
                                     SyncConfig.TableMapping tableMapping) {
        if (primaryKeys.size() == 1) {
            String pk = primaryKeys.get(0);
            String keys = keyValues.stream()
                    .map(k -> "'" + k.replace("'", "''") + "'")
                    .collect(Collectors.joining(","));
            return pk + " IN (" + keys + ")";
        } else {
            List<String> conditions = new ArrayList<>();
            for (String keyValue : keyValues) {
                String[] parts = keyValue.split("\\|");
                List<String> pkConditions = new ArrayList<>();
                for (int i = 0; i < primaryKeys.size() && i < parts.length; i++) {
                    pkConditions.add(primaryKeys.get(i) + " = '" + parts[i].replace("'", "''") + "'");
                }
                conditions.add("(" + String.join(" AND ", pkConditions) + ")");
            }
            return String.join(" OR ", conditions);
        }
    }

    public ValidationResult getLastValidationResult(String schema, String table) {
        return lastValidationResults.get(schema + "." + table);
    }

    public Map<String, ValidationResult> getAllLastValidationResults() {
        return new HashMap<>(lastValidationResults);
    }

    public long getLastValidationTime(String schema, String table) {
        Long timestamp = validationTimestamps.get(schema + "." + table);
        return timestamp != null ? timestamp : 0;
    }

    public void triggerValidationAsync() {
        validationExecutor.submit(this::validateAllTables);
    }

    public void shutdown() {
        validationExecutor.shutdown();
        try {
            if (!validationExecutor.awaitTermination(60, TimeUnit.SECONDS)) {
                validationExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            validationExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    private String getTableKey(SyncConfig.TableMapping tableMapping) {
        return tableMapping.getSourceSchema() + "." + tableMapping.getSourceTable();
    }
}

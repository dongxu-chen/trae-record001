package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ClickHouseWriterService {

    private final JdbcTemplate clickHouseJdbcTemplate;
    private final SyncConfig syncConfig;
    private final DataMappingService dataMappingService;
    private final ConflictResolutionService conflictResolutionService;
    private final MetricsService metricsService;

    private final Map<String, List<RowData>> writeBuffer = new ConcurrentHashMap<>();

    @Autowired
    public ClickHouseWriterService(@Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate,
                                   SyncConfig syncConfig,
                                   DataMappingService dataMappingService,
                                   ConflictResolutionService conflictResolutionService,
                                   MetricsService metricsService) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
        this.syncConfig = syncConfig;
        this.dataMappingService = dataMappingService;
        this.conflictResolutionService = conflictResolutionService;
        this.metricsService = metricsService;
    }

    public void write(List<RowData> rowDataList) {
        if (rowDataList == null || rowDataList.isEmpty()) {
            return;
        }

        Map<String, List<RowData>> groupedByTable = rowDataList.stream()
                .collect(Collectors.groupingBy(r -> r.getDatabase() + "." + r.getTable()));

        for (Map.Entry<String, List<RowData>> entry : groupedByTable.entrySet()) {
            writeToClickHouse(entry.getKey(), entry.getValue());
        }
    }

    private void writeToClickHouse(String tableKey, List<RowData> rowDataList) {
        SyncConfig.TableMapping tableMapping = dataMappingService.getTableMapping(
                rowDataList.get(0).getDatabase(),
                rowDataList.get(0).getTable()
        );

        if (tableMapping == null) {
            log.warn("No table mapping found for {}", tableKey);
            return;
        }

        try {
            List<RowData> resolvedData = conflictResolutionService.resolveConflicts(rowDataList, tableMapping);

            if (resolvedData.isEmpty()) {
                return;
            }

            String insertSql = buildInsertSQL(tableMapping, resolvedData);
            executeWrite(insertSql, tableMapping, resolvedData);

            metricsService.incrementClickHouseWriteSuccessCount(resolvedData.size());

            log.debug("Successfully wrote {} records to {}.{}",
                    resolvedData.size(),
                    tableMapping.getTargetDatabase(),
                    tableMapping.getTargetTable());

        } catch (Exception e) {
            log.error("Failed to write to ClickHouse for table {}", tableKey, e);
            metricsService.incrementClickHouseWriteErrorCount();

            int retryCount = 0;
            while (retryCount < syncConfig.getClickhouse().getMaxRetries()) {
                try {
                    Thread.sleep(syncConfig.getClickhouse().getRetryDelayMs());
                    String insertSql = buildInsertSQL(tableMapping, rowDataList);
                    executeWrite(insertSql, tableMapping, rowDataList);
                    metricsService.incrementClickHouseWriteSuccessCount(rowDataList.size());
                    log.info("Retry {} succeeded for table {}", retryCount + 1, tableKey);
                    return;
                } catch (Exception retryEx) {
                    log.error("Retry {} failed for table {}", retryCount + 1, tableKey, retryEx);
                    retryCount++;
                }
            }

            throw new RuntimeException("Failed to write to ClickHouse after " +
                    syncConfig.getClickhouse().getMaxRetries() + " retries", e);
        }
    }

    private String buildInsertSQL(SyncConfig.TableMapping tableMapping, List<RowData> rowDataList) {
        String targetDatabase = tableMapping.getTargetDatabase();
        String targetTable = tableMapping.getTargetTable();
        List<SyncConfig.ColumnMapping> columnMappings = dataMappingService.getEffectiveColumnMappings(tableMapping, rowDataList.get(0));

        StringBuilder sql = new StringBuilder();
        sql.append("INSERT INTO ").append(targetDatabase).append(".").append(targetTable);
        sql.append(" (");

        String columns = columnMappings.stream()
                .map(SyncConfig.ColumnMapping::getTarget)
                .collect(Collectors.joining(", "));
        sql.append(columns).append(") VALUES ");

        List<String> valueStrings = new ArrayList<>();
        for (RowData rowData : rowDataList) {
            Map<String, Object> mappedData = dataMappingService.mapRowData(rowData, tableMapping);
            String values = columnMappings.stream()
                    .map(cm -> formatValue(mappedData.get(cm.getTarget()), cm.getType()))
                    .collect(Collectors.joining(", "));
            valueStrings.add("(" + values + ")");
        }

        sql.append(String.join(", ", valueStrings));

        return sql.toString();
    }

    private String formatValue(Object value, String type) {
        if (value == null) {
            return "NULL";
        }

        String typeLower = type.toLowerCase();
        if (typeLower.contains("string") || typeLower.contains("varchar")
                || typeLower.contains("text") || typeLower.contains("date")) {
            return "'" + escapeString(value.toString()) + "'";
        } else if (typeLower.contains("bool")) {
            return value.toString();
        } else {
            return value.toString();
        }
    }

    private String escapeString(String value) {
        return value.replace("'", "''").replace("\\", "\\\\");
    }

    private void executeWrite(String sql, SyncConfig.TableMapping tableMapping, List<RowData> rowDataList) {
        long startTime = System.currentTimeMillis();
        try {
            clickHouseJdbcTemplate.execute(sql);
            long duration = System.currentTimeMillis() - startTime;
            metricsService.recordClickHouseWriteLatency(duration);
        } catch (Exception e) {
            throw new RuntimeException("ClickHouse execute failed: " + e.getMessage(), e);
        }
    }

    @Scheduled(fixedDelayString = "${sync.clickhouse.flush-interval-ms:5000}")
    public void flushBuffer() {
        for (Map.Entry<String, List<RowData>> entry : writeBuffer.entrySet()) {
            List<RowData> buffer = entry.getValue();
            if (!buffer.isEmpty()) {
                synchronized (buffer) {
                    if (!buffer.isEmpty()) {
                        List<RowData> copy = new ArrayList<>(buffer);
                        buffer.clear();
                        write(copy);
                    }
                }
            }
        }
    }

    public void delete(SyncConfig.TableMapping tableMapping, Map<String, Object> primaryKeyValues) {
        String targetDatabase = tableMapping.getTargetDatabase();
        String targetTable = tableMapping.getTargetTable();

        StringBuilder sql = new StringBuilder();
        sql.append("ALTER TABLE ").append(targetDatabase).append(".").append(targetTable);
        sql.append(" DELETE WHERE ");

        List<String> conditions = new ArrayList<>();
        for (String pk : tableMapping.getPrimaryKeys()) {
            Object value = primaryKeyValues.get(pk);
            conditions.add(pk + " = " + formatValue(value, "String"));
        }

        sql.append(String.join(" AND ", conditions));

        try {
            clickHouseJdbcTemplate.execute(sql.toString());
            log.debug("Deleted record from {}.{} with keys: {}", targetDatabase, targetTable, primaryKeyValues);
        } catch (Exception e) {
            log.error("Failed to delete from ClickHouse", e);
            throw new RuntimeException("Delete failed", e);
        }
    }

    public void createTableIfNotExists(SyncConfig.TableMapping tableMapping, Map<String, String> columnTypes) {
        String targetDatabase = tableMapping.getTargetDatabase();
        String targetTable = tableMapping.getTargetTable();

        StringBuilder sql = new StringBuilder();
        sql.append("CREATE TABLE IF NOT EXISTS ").append(targetDatabase).append(".").append(targetTable);
        sql.append(" (");

        List<String> columnDefs = new ArrayList<>();
        for (SyncConfig.ColumnMapping cm : tableMapping.getColumnMapping()) {
            String chType = columnTypes.getOrDefault(cm.getSource(), "String");
            columnDefs.add(cm.getTarget() + " " + chType);
        }

        sql.append(String.join(", ", columnDefs));
        sql.append(") ENGINE = ReplacingMergeTree()");

        if (!tableMapping.getPrimaryKeys().isEmpty()) {
            sql.append(" PRIMARY KEY (").append(String.join(", ", tableMapping.getPrimaryKeys())).append(")");
        }

        if (tableMapping.getPartitionKey() != null && !tableMapping.getPartitionKey().isEmpty()) {
            sql.append(" PARTITION BY ").append(tableMapping.getPartitionKey());
        }

        try {
            clickHouseJdbcTemplate.execute("CREATE DATABASE IF NOT EXISTS " + targetDatabase);
            clickHouseJdbcTemplate.execute(sql.toString());
            log.info("Created table {}.{} if not exists", targetDatabase, targetTable);
        } catch (Exception e) {
            log.error("Failed to create table {}.{}", targetDatabase, targetTable, e);
        }
    }
}

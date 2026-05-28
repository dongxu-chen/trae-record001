package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class FullSyncService {

    private final SyncConfig syncConfig;
    private final JdbcTemplate mysqlJdbcTemplate;
    private final ClickHouseWriterService clickHouseWriterService;
    private final DataMappingService dataMappingService;
    private final CheckpointService checkpointService;
    private final MetricsService metricsService;
    private final WatermarkManager watermarkManager;

    private final ExecutorService executorService = Executors.newFixedThreadPool(4);

    @Autowired
    public FullSyncService(SyncConfig syncConfig,
                           @Qualifier("mysqlJdbcTemplate") JdbcTemplate mysqlJdbcTemplate,
                           ClickHouseWriterService clickHouseWriterService,
                           DataMappingService dataMappingService,
                           CheckpointService checkpointService,
                           MetricsService metricsService,
                           WatermarkManager watermarkManager) {
        this.syncConfig = syncConfig;
        this.mysqlJdbcTemplate = mysqlJdbcTemplate;
        this.clickHouseWriterService = clickHouseWriterService;
        this.dataMappingService = dataMappingService;
        this.checkpointService = checkpointService;
        this.metricsService = metricsService;
        this.watermarkManager = watermarkManager;
    }

    @PostConstruct
    public void startFullSyncIfNeeded() {
        SyncConfig.SyncMode mode = syncConfig.getMode();

        if (mode == SyncConfig.SyncMode.FULL || mode == SyncConfig.SyncMode.FULL_INCREMENTAL) {
            log.info("Starting full sync in mode: {}", mode);
            executorService.submit(this::performFullSync);
        } else {
            log.info("Full sync skipped, current mode: {}", mode);
        }
    }

    public void performFullSync() {
        log.info("Full sync started");
        metricsService.incrementFullSyncCount();

        List<SyncConfig.TableMapping> tablesToSync = syncConfig.getTables().stream()
                .filter(t -> t.getSyncMode() == SyncConfig.SyncMode.FULL
                        || t.getSyncMode() == SyncConfig.SyncMode.FULL_INCREMENTAL)
                .toList();

        for (SyncConfig.TableMapping tableMapping : tablesToSync) {
            try {
                syncTable(tableMapping);
            } catch (Exception e) {
                log.error("Full sync failed for table {}.{}",
                        tableMapping.getSourceSchema(), tableMapping.getSourceTable(), e);
            }
        }

        log.info("Full sync completed");
        checkpointService.forceSave();
    }

    private void syncTable(SyncConfig.TableMapping tableMapping) {
        String sourceSchema = tableMapping.getSourceSchema();
        String sourceTable = tableMapping.getSourceTable();
        String fullTableName = sourceSchema + "." + sourceTable;

        log.info("Starting full sync for table: {}", fullTableName);

        if (watermarkManager.isFullSyncCompleted(sourceSchema, sourceTable)) {
            log.info("Watermark indicates full sync already completed for {}, skipping", fullTableName);
            return;
        }

        try {
            Map<String, Object> masterStatus = getCurrentBinlogPosition();
            String binlogFileName = (String) masterStatus.get("File");
            long binlogPosition = ((Number) masterStatus.get("Position")).longValue();

            watermarkManager.recordFullSyncStart(sourceSchema, sourceTable,
                    binlogFileName, binlogPosition);

            long totalRows = getRowCount(sourceSchema, sourceTable);
            log.info("Total rows to sync for {}: {}", fullTableName, totalRows);

            if (totalRows == 0) {
                log.info("Table {} is empty, skipping", fullTableName);
                watermarkManager.recordFullSyncEnd(sourceSchema, sourceTable);
                checkpointService.updateCheckpoint(sourceSchema, sourceTable, "FULL", 0, System.currentTimeMillis());
                return;
            }

            int fetchSize = syncConfig.getMysql().getFetchSize();
            int batchSize = syncConfig.getClickhouse().getBatchSize();
            long offset = 0;
            long processedRows = 0;

            Map<String, String> columnTypes = null;

            while (offset < totalRows) {
                List<RowData> batch = fetchBatch(sourceSchema, sourceTable, offset, fetchSize);

                if (batch.isEmpty()) {
                    break;
                }

                if (columnTypes == null && !batch.isEmpty()) {
                    columnTypes = dataMappingService.getColumnTypeMap(batch.get(0));
                    clickHouseWriterService.createTableIfNotExists(tableMapping, columnTypes);
                }

                clickHouseWriterService.write(batch);

                processedRows += batch.size();
                offset += fetchSize;

                metricsService.incrementFullSyncProgress(fullTableName, processedRows, totalRows);
                log.debug("Synced {}/{} rows for {}", processedRows, totalRows, fullTableName);
            }

            watermarkManager.recordFullSyncEnd(sourceSchema, sourceTable);
            checkpointService.updateCheckpoint(sourceSchema, sourceTable, "FULL", processedRows, System.currentTimeMillis());
            log.info("Full sync completed for {}, total rows: {}", fullTableName, processedRows);

        } catch (Exception e) {
            log.error("Full sync failed for table: {}", fullTableName, e);
            watermarkManager.recordFullSyncFailed(sourceSchema, sourceTable, e.getMessage());
            throw new RuntimeException("Full sync failed for " + fullTableName, e);
        }
    }

    private Map<String, Object> getCurrentBinlogPosition() {
        try {
            return mysqlJdbcTemplate.queryForObject("SHOW MASTER STATUS", (rs, rowNum) -> {
                Map<String, Object> result = new HashMap<>();
                ResultSetMetaData metaData = rs.getMetaData();
                for (int i = 1; i <= metaData.getColumnCount(); i++) {
                    result.put(metaData.getColumnName(i), rs.getObject(i));
                }
                return result;
            });
        } catch (Exception e) {
            log.error("Failed to get current binlog position", e);
            Map<String, Object> defaultStatus = new HashMap<>();
            defaultStatus.put("File", "");
            defaultStatus.put("Position", 0);
            return defaultStatus;
        }
    }

    private long getRowCount(String schema, String table) {
        String sql = "SELECT COUNT(*) FROM " + schema + "." + table;
        return mysqlJdbcTemplate.queryForObject(sql, Long.class);
    }

    private List<RowData> fetchBatch(String schema, String table, long offset, int limit) {
        String sql = "SELECT * FROM " + schema + "." + table + " LIMIT ?, ?";

        return mysqlJdbcTemplate.query(sql, ps -> {
            ps.setLong(1, offset);
            ps.setInt(2, limit);
            ps.setFetchSize(limit);
        }, rs -> {
            List<RowData> result = new ArrayList<>();
            ResultSetMetaData metaData = rs.getMetaData();
            int columnCount = metaData.getColumnCount();

            Map<String, RowData.ColumnInfo> columnInfoMap = new LinkedHashMap<>();
            for (int i = 1; i <= columnCount; i++) {
                RowData.ColumnInfo info = RowData.ColumnInfo.builder()
                        .name(metaData.getColumnName(i))
                        .mysqlType(metaData.getColumnTypeName(i))
                        .isNullable(metaData.isNullable(i) == ResultSetMetaData.columnNullable)
                        .index(i - 1)
                        .build();
                columnInfoMap.put(info.getName(), info);
            }

            while (rs.next()) {
                Map<String, Object> data = new LinkedHashMap<>();
                for (int i = 1; i <= columnCount; i++) {
                    String columnName = metaData.getColumnName(i);
                    Object value = rs.getObject(i);
                    data.put(columnName, value);
                }

                RowData rowData = RowData.builder()
                        .database(schema)
                        .table(table)
                        .eventType(RowData.EventType.INSERT)
                        .afterData(data)
                        .columns(columnInfoMap)
                        .timestamp(System.currentTimeMillis())
                        .binlogFileName("FULL_SYNC")
                        .binlogPosition(offset + rs.getRow())
                        .build();

                result.add(rowData);
            }

            return result;
        });
    }

    public void shutdown() {
        executorService.shutdown();
        try {
            if (!executorService.awaitTermination(60, TimeUnit.SECONDS)) {
                executorService.shutdownNow();
            }
        } catch (InterruptedException e) {
            executorService.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    public boolean isFullSyncComplete(String schema, String table) {
        return checkpointService.hasCheckpoint(schema, table);
    }
}

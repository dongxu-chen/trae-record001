package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.DDLEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class DDLSyncService {

    private final JdbcTemplate clickHouseJdbcTemplate;
    private final SyncConfig syncConfig;
    private final DataMappingService dataMappingService;

    private final Map<String, Boolean> tableExistsCache = new ConcurrentHashMap<>();

    @Autowired
    public DDLSyncService(@Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate,
                          SyncConfig syncConfig,
                          DataMappingService dataMappingService) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
        this.syncConfig = syncConfig;
        this.dataMappingService = dataMappingService;
    }

    public void processDDL(DDLEvent ddlEvent) {
        if (ddlEvent == null) {
            return;
        }

        SyncConfig.TableMapping tableMapping = dataMappingService.getTableMapping(
                ddlEvent.getDatabase(), ddlEvent.getTable());

        if (tableMapping == null) {
            log.debug("No table mapping found for DDL event: {}.{}",
                    ddlEvent.getDatabase(), ddlEvent.getTable());
            return;
        }

        try {
            switch (ddlEvent.getDdlType()) {
                case CREATE_TABLE:
                    handleCreateTable(ddlEvent, tableMapping);
                    break;
                case ALTER_TABLE:
                    handleAlterTable(ddlEvent, tableMapping);
                    break;
                case DROP_TABLE:
                    handleDropTable(ddlEvent, tableMapping);
                    break;
                case TRUNCATE_TABLE:
                    handleTruncateTable(ddlEvent, tableMapping);
                    break;
                case RENAME_TABLE:
                    handleRenameTable(ddlEvent, tableMapping);
                    break;
                default:
                    log.info("Unsupported DDL type: {} for table {}.{}",
                            ddlEvent.getDdlType(), ddlEvent.getDatabase(), ddlEvent.getTable());
            }
        } catch (Exception e) {
            log.error("Failed to process DDL event: {}", ddlEvent.getSql(), e);
        }
    }

    private void handleCreateTable(DDLEvent ddlEvent, SyncConfig.TableMapping tableMapping) {
        log.info("Processing CREATE TABLE DDL for {}.{} -> {}.{}",
                ddlEvent.getDatabase(), ddlEvent.getTable(),
                tableMapping.getTargetDatabase(), tableMapping.getTargetTable());

        Map<String, String> columnTypes = new java.util.LinkedHashMap<>();
        for (DDLEvent.ColumnChange change : ddlEvent.getColumnChanges()) {
            String chType = convertToClickHouseType(change.getDataType(), change.getLength(), change.getScale());
            columnTypes.put(change.getColumnName(), chType);
        }

        try {
            createDatabaseIfNotExists(tableMapping.getTargetDatabase());
            String createSQL = buildCreateTableSQL(tableMapping, columnTypes);
            clickHouseJdbcTemplate.execute(createSQL);
            log.info("Created ClickHouse table: {}.{}",
                    tableMapping.getTargetDatabase(), tableMapping.getTargetTable());
            tableExistsCache.put(getFullTableName(tableMapping), true);
        } catch (Exception e) {
            log.error("Failed to create ClickHouse table", e);
        }
    }

    private void handleAlterTable(DDLEvent ddlEvent, SyncConfig.TableMapping tableMapping) {
        log.info("Processing ALTER TABLE DDL for {}.{} -> {}.{}",
                ddlEvent.getDatabase(), ddlEvent.getTable(),
                tableMapping.getTargetDatabase(), tableMapping.getTargetTable());

        for (DDLEvent.ColumnChange change : ddlEvent.getColumnChanges()) {
            try {
                String alterSQL = buildAlterColumnSQL(tableMapping, change);
                if (alterSQL != null) {
                    clickHouseJdbcTemplate.execute(alterSQL);
                    log.info("Executed ALTER TABLE on {}.{}: {}",
                            tableMapping.getTargetDatabase(),
                            tableMapping.getTargetTable(), alterSQL);
                }
            } catch (Exception e) {
                log.error("Failed to execute ALTER TABLE for column: {}", change.getColumnName(), e);
            }
        }
    }

    private void handleDropTable(DDLEvent ddlEvent, SyncConfig.TableMapping tableMapping) {
        log.warn("Received DROP TABLE DDL for {}.{}, but keeping ClickHouse table {}.{}",
                ddlEvent.getDatabase(), ddlEvent.getTable(),
                tableMapping.getTargetDatabase(), tableMapping.getTargetTable());
    }

    private void handleTruncateTable(DDLEvent ddlEvent, SyncConfig.TableMapping tableMapping) {
        log.info("Processing TRUNCATE TABLE DDL for {}.{}",
                ddlEvent.getDatabase(), ddlEvent.getTable());

        try {
            String truncateSQL = "TRUNCATE TABLE " + tableMapping.getTargetDatabase()
                    + "." + tableMapping.getTargetTable();
            clickHouseJdbcTemplate.execute(truncateSQL);
            log.info("Truncated ClickHouse table: {}.{}",
                    tableMapping.getTargetDatabase(), tableMapping.getTargetTable());
        } catch (Exception e) {
            log.error("Failed to truncate ClickHouse table", e);
        }
    }

    private void handleRenameTable(DDLEvent ddlEvent, SyncConfig.TableMapping tableMapping) {
        log.info("Received RENAME TABLE DDL for {}.{}, but keeping ClickHouse table name: {}.{}",
                ddlEvent.getDatabase(), ddlEvent.getTable(),
                tableMapping.getTargetDatabase(), tableMapping.getTargetTable());
    }

    private String buildCreateTableSQL(SyncConfig.TableMapping tableMapping,
                                       Map<String, String> columnTypes) {
        StringBuilder sql = new StringBuilder();
        sql.append("CREATE TABLE IF NOT EXISTS ").append(tableMapping.getTargetDatabase())
                .append(".").append(tableMapping.getTargetTable()).append(" (");

        List<String> columnDefs = new java.util.ArrayList<>();

        if (tableMapping.getColumnMapping() != null && !tableMapping.getColumnMapping().isEmpty()) {
            for (SyncConfig.ColumnMapping cm : tableMapping.getColumnMapping()) {
                String chType = cm.getType() != null ? cm.getType() :
                        columnTypes.getOrDefault(cm.getSource(), "String");
                columnDefs.add(cm.getTarget() + " " + chType);
            }
        } else {
            for (Map.Entry<String, String> entry : columnTypes.entrySet()) {
                columnDefs.add(entry.getKey() + " " + entry.getValue());
            }
        }

        sql.append(String.join(", ", columnDefs));
        sql.append(") ENGINE = ReplacingMergeTree()");

        if (!tableMapping.getPrimaryKeys().isEmpty()) {
            sql.append(" PRIMARY KEY (").append(String.join(", ", tableMapping.getPrimaryKeys())).append(")");
        }

        if (tableMapping.getPartitionKey() != null && !tableMapping.getPartitionKey().isEmpty()) {
            sql.append(" PARTITION BY ").append(tableMapping.getPartitionKey());
        }

        return sql.toString();
    }

    private String buildAlterColumnSQL(SyncConfig.TableMapping tableMapping,
                                       DDLEvent.ColumnChange change) {
        String targetColumn = getTargetColumn(tableMapping, change.getColumnName());
        String chType = convertToClickHouseType(change.getDataType(), change.getLength(), change.getScale());

        StringBuilder sql = new StringBuilder();
        sql.append("ALTER TABLE ").append(tableMapping.getTargetDatabase())
                .append(".").append(tableMapping.getTargetTable());

        switch (change.getChangeType()) {
            case ADD:
                sql.append(" ADD COLUMN ").append(targetColumn).append(" ").append(chType);
                if (change.getAfterColumn() != null) {
                    String afterTarget = getTargetColumn(tableMapping, change.getAfterColumn());
                    sql.append(" AFTER ").append(afterTarget);
                }
                break;
            case MODIFY:
                sql.append(" MODIFY COLUMN ").append(targetColumn).append(" ").append(chType);
                break;
            case DROP:
                sql.append(" DROP COLUMN ").append(targetColumn);
                break;
            case CHANGE:
            case RENAME:
                String oldTarget = getTargetColumn(tableMapping, change.getOldColumnName());
                sql.append(" RENAME COLUMN ").append(oldTarget).append(" TO ").append(targetColumn);
                break;
            default:
                return null;
        }

        return sql.toString();
    }

    private String getTargetColumn(SyncConfig.TableMapping tableMapping, String sourceColumn) {
        if (tableMapping.getColumnMapping() == null || tableMapping.getColumnMapping().isEmpty()) {
            return sourceColumn;
        }

        for (SyncConfig.ColumnMapping cm : tableMapping.getColumnMapping()) {
            if (cm.getSource().equals(sourceColumn)) {
                return cm.getTarget();
            }
        }

        return sourceColumn;
    }

    private String convertToClickHouseType(String mysqlType, Integer length, Integer scale) {
        if (mysqlType == null) {
            return "String";
        }

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
            int precision = length != null ? length : 18;
            int decimalScale = scale != null ? scale : 4;
            return "Decimal(" + precision + "," + decimalScale + ")";
        } else if (typeLower.contains("datetime") || typeLower.contains("timestamp")) {
            return "DateTime";
        } else if (typeLower.contains("date")) {
            return "Date";
        } else if (typeLower.contains("json")) {
            return "String";
        } else if (typeLower.contains("blob") || typeLower.contains("binary")) {
            return "String";
        } else if (typeLower.contains("char") || typeLower.contains("varchar") || typeLower.contains("text")) {
            if (length != null && length <= 255) {
                return "FixedString(" + length + ")";
            }
            return "String";
        } else {
            return "String";
        }
    }

    private void createDatabaseIfNotExists(String database) {
        try {
            clickHouseJdbcTemplate.execute("CREATE DATABASE IF NOT EXISTS " + database);
        } catch (Exception e) {
            log.warn("Failed to create database: {}", database, e);
        }
    }

    private String getFullTableName(SyncConfig.TableMapping tableMapping) {
        return tableMapping.getTargetDatabase() + "." + tableMapping.getTargetTable();
    }

    public boolean isTableExists(SyncConfig.TableMapping tableMapping) {
        String key = getFullTableName(tableMapping);
        Boolean exists = tableExistsCache.get(key);
        if (exists != null) {
            return exists;
        }

        try {
            String sql = "EXISTS TABLE " + getFullTableName(tableMapping);
            Integer result = clickHouseJdbcTemplate.queryForObject(sql, Integer.class);
            boolean tableExists = result != null && result == 1;
            tableExistsCache.put(key, tableExists);
            return tableExists;
        } catch (Exception e) {
            log.warn("Failed to check table existence: {}", key, e);
            return false;
        }
    }
}

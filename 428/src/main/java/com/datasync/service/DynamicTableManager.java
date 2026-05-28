package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Slf4j
@Service
public class DynamicTableManager {

    private final SyncConfig syncConfig;
    private final JdbcTemplate mysqlJdbcTemplate;
    private final ObjectMapper objectMapper;
    private final DDLSyncService ddlSyncService;
    private final ClickHouseWriterService clickHouseWriterService;

    private final Map<String, SyncConfig.TableMapping> dynamicTables = new ConcurrentHashMap<>();
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();
    private static final String DYNAMIC_TABLES_FILE = "./config/dynamic_tables.json";

    @Autowired
    public DynamicTableManager(SyncConfig syncConfig,
                               @Qualifier("mysqlJdbcTemplate") JdbcTemplate mysqlJdbcTemplate,
                               ObjectMapper objectMapper,
                               DDLSyncService ddlSyncService,
                               ClickHouseWriterService clickHouseWriterService) {
        this.syncConfig = syncConfig;
        this.mysqlJdbcTemplate = mysqlJdbcTemplate;
        this.objectMapper = objectMapper;
        this.ddlSyncService = ddlSyncService;
        this.clickHouseWriterService = clickHouseWriterService;
    }

    @PostConstruct
    public void init() {
        loadDynamicTables();
    }

    @Scheduled(fixedDelay = 60000)
    public void autoDiscoverNewTables() {
        if (!syncConfig.isAutoDiscoverTables()) {
            return;
        }

        try {
            List<String> schemas = syncConfig.getAutoDiscoverSchemas();
            if (schemas == null || schemas.isEmpty()) {
                return;
            }

            for (String schema : schemas) {
                discoverTablesInSchema(schema);
            }
        } catch (Exception e) {
            log.error("Auto discover tables failed", e);
        }
    }

    private void discoverTablesInSchema(String schema) {
        try {
            List<String> existingTables = getAllTablesInSchema(schema);
            Set<String> configuredTables = getConfiguredTables(schema);

            for (String table : existingTables) {
                String tableKey = schema + "." + table;
                if (!configuredTables.contains(tableKey) && !dynamicTables.containsKey(tableKey)) {
                    log.info("Discovered new table: {}.{}, adding to sync", schema, table);
                    try {
                        addTable(schema, table, null);
                    } catch (Exception e) {
                        log.error("Failed to add discovered table: {}.{}", schema, table, e);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to discover tables in schema: {}", schema, e);
        }
    }

    private List<String> getAllTablesInSchema(String schema) {
        String sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = ? AND table_type = 'BASE TABLE'";
        return mysqlJdbcTemplate.queryForList(sql, String.class, schema);
    }

    private Set<String> getConfiguredTables(String schema) {
        Set<String> tables = new HashSet<>();
        for (SyncConfig.TableMapping mapping : syncConfig.getTables()) {
            if (mapping.getSourceSchema().equals(schema)) {
                tables.add(mapping.getSourceSchema() + "." + mapping.getSourceTable());
            }
        }
        for (String key : dynamicTables.keySet()) {
            if (key.startsWith(schema + ".")) {
                tables.add(key);
            }
        }
        return tables;
    }

    public SyncConfig.TableMapping addTable(String sourceSchema, String sourceTable,
                                             SyncConfig.TableMapping customMapping) {
        lock.writeLock().lock();
        try {
            String tableKey = sourceSchema + "." + sourceTable;

            if (dynamicTables.containsKey(tableKey)) {
                log.warn("Table already exists in dynamic config: {}", tableKey);
                return dynamicTables.get(tableKey);
            }

            SyncConfig.TableMapping mapping;
            if (customMapping != null) {
                mapping = customMapping;
            } else {
                mapping = createDefaultMapping(sourceSchema, sourceTable);
            }

            dynamicTables.put(tableKey, mapping);
            saveDynamicTables();

            try {
                Map<String, String> columnTypes = getTableColumnTypes(sourceSchema, sourceTable);
                clickHouseWriterService.createTableIfNotExists(mapping, columnTypes);
                log.info("Successfully added table to sync: {}", tableKey);
            } catch (Exception e) {
                log.warn("Failed to create ClickHouse table for {}, but mapping added", tableKey, e);
            }

            return mapping;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public boolean removeTable(String sourceSchema, String sourceTable) {
        lock.writeLock().lock();
        try {
            String tableKey = sourceSchema + "." + sourceTable;
            SyncConfig.TableMapping removed = dynamicTables.remove(tableKey);
            if (removed != null) {
                saveDynamicTables();
                log.info("Removed table from sync: {}", tableKey);
                return true;
            }
            return false;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public SyncConfig.TableMapping updateTable(String sourceSchema, String sourceTable,
                                                SyncConfig.TableMapping updatedMapping) {
        lock.writeLock().lock();
        try {
            String tableKey = sourceSchema + "." + sourceTable;
            dynamicTables.put(tableKey, updatedMapping);
            saveDynamicTables();
            log.info("Updated table mapping: {}", tableKey);
            return updatedMapping;
        } finally {
            lock.writeLock().unlock();
        }
    }

    private SyncConfig.TableMapping createDefaultMapping(String sourceSchema, String sourceTable) {
        SyncConfig.TableMapping mapping = new SyncConfig.TableMapping();
        mapping.setSourceSchema(sourceSchema);
        mapping.setSourceTable(sourceTable);
        mapping.setTargetDatabase(sourceSchema);
        mapping.setTargetTable(sourceTable);
        mapping.setSyncMode(SyncConfig.SyncMode.INCREMENTAL);
        mapping.setConflictStrategy(SyncConfig.ConflictStrategy.UPDATE);

        List<SyncConfig.ColumnMapping> columnMappings = new ArrayList<>();
        try {
            List<Map<String, Object>> columns = getTableColumns(sourceSchema, sourceTable);
            for (Map<String, Object> column : columns) {
                SyncConfig.ColumnMapping cm = new SyncConfig.ColumnMapping();
                String columnName = (String) column.get("COLUMN_NAME");
                cm.setSource(columnName);
                cm.setTarget(columnName);
                cm.setType(convertToClickHouseType((String) column.get("DATA_TYPE"),
                        (Number) column.get("CHARACTER_MAXIMUM_LENGTH"),
                        (Number) column.get("NUMERIC_SCALE")));
                columnMappings.add(cm);

                if ("PRI".equals(column.get("COLUMN_KEY"))) {
                    mapping.getPrimaryKeys().add(columnName);
                }
            }
        } catch (Exception e) {
            log.warn("Failed to get columns for {}.{}, using empty mapping", sourceSchema, sourceTable, e);
        }

        mapping.setColumnMapping(columnMappings);
        return mapping;
    }

    private List<Map<String, Object>> getTableColumns(String schema, String table) {
        String sql = "SELECT column_name, data_type, character_maximum_length, numeric_scale, column_key " +
                "FROM information_schema.columns WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position";
        return mysqlJdbcTemplate.queryForList(sql, schema, table);
    }

    private Map<String, String> getTableColumnTypes(String schema, String table) {
        Map<String, String> columnTypes = new LinkedHashMap<>();
        try {
            String sql = "SELECT * FROM " + schema + "." + table + " LIMIT 1";
            mysqlJdbcTemplate.query(sql, rs -> {
                ResultSetMetaData metaData = rs.getMetaData();
                for (int i = 1; i <= metaData.getColumnCount(); i++) {
                    columnTypes.put(metaData.getColumnName(i), metaData.getColumnTypeName(i));
                }
            });
        } catch (Exception e) {
            log.warn("Failed to get column types for {}.{}", schema, table, e);
        }
        return columnTypes;
    }

    private String convertToClickHouseType(String mysqlType, Number length, Number scale) {
        if (mysqlType == null) return "String";

        String typeLower = mysqlType.toLowerCase();
        if (typeLower.contains("tinyint") || typeLower.contains("bool")) return "UInt8";
        if (typeLower.contains("smallint")) return "Int16";
        if (typeLower.contains("mediumint")) return "Int32";
        if (typeLower.contains("bigint")) return "Int64";
        if (typeLower.contains("int")) return "Int32";
        if (typeLower.contains("float")) return "Float32";
        if (typeLower.contains("double") || typeLower.contains("real")) return "Float64";
        if (typeLower.contains("decimal") || typeLower.contains("numeric")) {
            int precision = length != null ? length.intValue() : 18;
            int decimalScale = scale != null ? scale.intValue() : 4;
            return "Decimal(" + precision + "," + decimalScale + ")";
        }
        if (typeLower.contains("datetime") || typeLower.contains("timestamp")) return "DateTime";
        if (typeLower.contains("date")) return "Date";
        if (typeLower.contains("json")) return "String";
        if (typeLower.contains("blob") || typeLower.contains("binary")) return "String";
        if (typeLower.contains("char") || typeLower.contains("varchar") || typeLower.contains("text")) {
            if (length != null && length.intValue() <= 255) {
                return "FixedString(" + length.intValue() + ")";
            }
            return "String";
        }
        return "String";
    }

    public List<SyncConfig.TableMapping> getAllTables() {
        lock.readLock().lock();
        try {
            List<SyncConfig.TableMapping> allTables = new ArrayList<>(syncConfig.getTables());
            allTables.addAll(dynamicTables.values());
            return allTables;
        } finally {
            lock.readLock().unlock();
        }
    }

    public SyncConfig.TableMapping getTable(String sourceSchema, String sourceTable) {
        lock.readLock().lock();
        try {
            String tableKey = sourceSchema + "." + sourceTable;
            SyncConfig.TableMapping mapping = syncConfig.getTables().stream()
                    .filter(t -> t.getSourceSchema().equals(sourceSchema) && t.getSourceTable().equals(sourceTable))
                    .findFirst()
                    .orElse(null);
            if (mapping == null) {
                mapping = dynamicTables.get(tableKey);
            }
            return mapping;
        } finally {
            lock.readLock().unlock();
        }
    }

    public List<SyncConfig.TableMapping> getDynamicTables() {
        lock.readLock().lock();
        try {
            return new ArrayList<>(dynamicTables.values());
        } finally {
            lock.readLock().unlock();
        }
    }

    private void loadDynamicTables() {
        try {
            Path path = Paths.get(DYNAMIC_TABLES_FILE);
            if (!Files.exists(path)) {
                log.info("No dynamic tables file found");
                return;
            }

            String content = new String(Files.readAllBytes(path));
            List<SyncConfig.TableMapping> tables = objectMapper.readValue(content,
                    new TypeReference<List<SyncConfig.TableMapping>>() {});

            for (SyncConfig.TableMapping table : tables) {
                String key = table.getSourceSchema() + "." + table.getSourceTable();
                dynamicTables.put(key, table);
            }

            log.info("Loaded {} dynamic tables", dynamicTables.size());
        } catch (Exception e) {
            log.error("Failed to load dynamic tables", e);
        }
    }

    private void saveDynamicTables() {
        try {
            Path path = Paths.get(DYNAMIC_TABLES_FILE);
            Files.createDirectories(path.getParent());

            List<SyncConfig.TableMapping> tables = new ArrayList<>(dynamicTables.values());
            String content = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(tables);
            Files.write(path, content.getBytes());

            log.debug("Saved {} dynamic tables", tables.size());
        } catch (Exception e) {
            log.error("Failed to save dynamic tables", e);
        }
    }

    public boolean isTableConfigured(String schema, String table) {
        return getTable(schema, table) != null;
    }

    public Map<String, Object> getTableStats(String schema, String table) {
        Map<String, Object> stats = new HashMap<>();
        try {
            String countSql = "SELECT COUNT(*) FROM " + schema + "." + table;
            Long rowCount = mysqlJdbcTemplate.queryForObject(countSql, Long.class);
            stats.put("sourceRowCount", rowCount);
        } catch (Exception e) {
            stats.put("sourceRowCount", -1);
        }
        return stats;
    }
}

package com.datasync.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.ArrayList;
import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "sync")
public class SyncConfig {

    private SyncMode mode = SyncMode.INCREMENTAL;

    private CanalConfig canal = new CanalConfig();

    private KafkaConfig kafka = new KafkaConfig();

    private ClickHouseConfig clickhouse = new ClickHouseConfig();

    private AutoDiscoverConfig autoDiscover = new AutoDiscoverConfig();

    private MySQLConfig mysql = new MySQLConfig();

    private CheckpointConfig checkpoint = new CheckpointConfig();

    private List<TableMapping> tables = new ArrayList<>();

    public enum SyncMode {
        FULL,
        INCREMENTAL,
        FULL_INCREMENTAL
    }

    @Data
    public static class CanalConfig {
        private String host = "localhost";
        private int port = 11111;
        private String destination = "example";
        private String username = "canal";
        private String password = "canal";
        private int batchSize = 1000;
        private String subscribeFilter = ".*\\..*";
    }

    @Data
    public static class KafkaConfig {
        private boolean enabled = true;
        private String topicPrefix = "mysql_ch_sync_";
    }

    @Data
    public static class AutoDiscoverConfig {
        private boolean enabled = false;
        private List<String> schemas = new ArrayList<>();
    }

    public boolean isAutoDiscoverTables() {
        return autoDiscover != null && autoDiscover.isEnabled();
    }

    public List<String> getAutoDiscoverSchemas() {
        return autoDiscover != null ? autoDiscover.getSchemas() : new ArrayList<>();
    }

    @Data
    public static class ClickHouseConfig {
        private String url = "jdbc:clickhouse://localhost:8123/default";
        private String username = "default";
        private String password = "";
        private String database = "default";
        private int batchSize = 1000;
        private long flushIntervalMs = 5000;
        private int maxRetries = 3;
        private long retryDelayMs = 1000;
        private ConnectionPoolConfig connectionPool = new ConnectionPoolConfig();
    }

    @Data
    public static class ConnectionPoolConfig {
        private int maximumPoolSize = 20;
        private int minimumIdle = 5;
        private long connectionTimeout = 30000;
        private long idleTimeout = 60000;
    }

    @Data
    public static class MySQLConfig {
        private String url = "jdbc:mysql://localhost:3306";
        private String username = "root";
        private String password = "root";
        private int fetchSize = 1000;
    }

    @Data
    public static class CheckpointConfig {
        private boolean enabled = true;
        private CheckpointType type = CheckpointType.FILE;
        private String filePath = "./checkpoint";
        private long intervalMs = 5000;
    }

    public enum CheckpointType {
        FILE,
        REDIS,
        JDBC
    }

    @Data
    public static class TableMapping {
        private String sourceSchema;
        private String sourceTable;
        private String targetDatabase;
        private String targetTable;
        private SyncMode syncMode = SyncMode.INCREMENTAL;
        private ConflictStrategy conflictStrategy = ConflictStrategy.UPDATE;
        private List<ColumnMapping> columnMapping = new ArrayList<>();
        private String partitionKey;
        private List<String> primaryKeys = new ArrayList<>();
    }

    public enum ConflictStrategy {
        UPDATE,
        IGNORE,
        THROW,
        VERSION
    }

    @Data
    public static class ColumnMapping {
        private String source;
        private String target;
        private String type;
        private String expression;
        private String defaultValue;
    }
}

package com.datasync.cdc.debezium;

import com.datasync.common.enums.DatabaseType;
import lombok.Builder;
import lombok.Data;

import java.util.Properties;

@Data
@Builder
public class DebeziumConnectorConfig {
    private String connectorId;

    private String databaseId;

    private String datacenterId;

    private DatabaseType databaseType;

    private String hostname;

    private int port;

    private String databaseName;

    private String username;

    private String password;

    private String serverId;

    private String serverName;

    private String tableIncludeList;

    private String slotName;

    private String pluginName;

    private String offsetStorage;

    private String offsetStorageFile;

    private String schemaHistoryInternal;

    private String schemaHistoryFile;

    private String businessKeyColumn;

    private String versionColumn;

    private String timestampColumn;

    public Properties toProperties() {
        Properties props = new Properties();
        props.setProperty("name", connectorId);
        props.setProperty("connector.class", getConnectorClass());
        props.setProperty("database.hostname", hostname);
        props.setProperty("database.port", String.valueOf(port));
        props.setProperty("database.user", username);
        props.setProperty("database.password", password);
        props.setProperty("database.dbname", databaseName);
        props.setProperty("database.server.name", serverName);
        props.setProperty("table.include.list", tableIncludeList);
        props.setProperty("offset.storage", offsetStorage);
        props.setProperty("offset.storage.file.filename", offsetStorageFile);
        props.setProperty("schema.history.internal", schemaHistoryInternal);
        props.setProperty("schema.history.internal.file.filename", schemaHistoryFile);
        props.setProperty("topic.prefix", serverName);

        if (databaseType == DatabaseType.POSTGRESQL) {
            if (slotName != null) {
                props.setProperty("slot.name", slotName);
            }
            if (pluginName != null) {
                props.setProperty("plugin.name", pluginName);
            }
        } else if (databaseType == DatabaseType.MYSQL) {
            props.setProperty("database.server.id", serverId);
        }

        return props;
    }

    private String getConnectorClass() {
        if (databaseType == DatabaseType.MYSQL) {
            return "io.debezium.connector.mysql.MySqlConnector";
        } else if (databaseType == DatabaseType.POSTGRESQL) {
            return "io.debezium.connector.postgresql.PostgresConnector";
        }
        throw new IllegalArgumentException("Unsupported database type: " + databaseType);
    }
}

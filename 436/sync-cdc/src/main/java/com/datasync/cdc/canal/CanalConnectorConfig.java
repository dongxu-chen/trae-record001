package com.datasync.cdc.canal;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CanalConnectorConfig {
    private String connectorId;

    private String databaseId;

    private String datacenterId;

    private String hostname;

    private int port;

    private String destination;

    private String username;

    private String password;

    private String subscribeFilter;

    private int batchSize;

    private long pollTimeoutMs;

    private String businessKeyColumn;

    private String versionColumn;

    private String timestampColumn;
}

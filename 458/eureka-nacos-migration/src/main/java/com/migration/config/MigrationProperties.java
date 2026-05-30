package com.migration.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "migration")
public class MigrationProperties {

    private int batchSize = 50;
    private int retryTimes = 3;
    private long retryIntervalMs = 2000;
    private long heartbeatIntervalMs = 5000;
    private long verifyIntervalMs = 10000;
    private double grayscaleRatio = 0.1;
    private boolean autoRollbackOnFailure = true;
    private long consistencyCheckTimeoutMs = 30000;
}

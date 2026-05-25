package com.tracking.collector.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "tracking.collector")
public class CollectorConfig {

    private int batchSize = 100;
    private long flushIntervalMs = 1000;
    private int maxQueueSize = 100000;
    private boolean enableIpParse = true;
    private boolean enableUserAgentParse = true;
    private List<String> allowedAppIds;

    public boolean isAppIdAllowed(String appId) {
        if (allowedAppIds == null || allowedAppIds.isEmpty()) {
            return true;
        }
        return allowedAppIds.contains(appId);
    }
}

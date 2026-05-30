package com.apiversion.gateway.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "api.version.rate-limit")
public class RateLimitConfig {

    private boolean enabled = true;

    private int maxRequestsPerSecond = 1000;

    private int burstCapacity = 2000;

    private int batchSize = 100;

    private int batchIntervalMs = 1000;

    private int warmUpPeriodSec = 60;
}

package com.hotconfig.sample.config;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import lombok.Data;
import org.springframework.stereotype.Component;

@Data
@Component
@HotConfig(prefix = "app")
public class AppConfig {

    @HotValue(value = "name", defaultValue = "hot-config-demo")
    private String appName;

    @HotValue(value = "version", defaultValue = "1.0.0")
    private String version;

    @HotValue(value = "env", defaultValue = "dev")
    private String env;

    @HotValue(value = "feature.toggle", defaultValue = "false")
    private Boolean featureToggle;

    @HotValue(value = "connection.timeout", defaultValue = "3000")
    private Integer connectionTimeout;

    @HotValue(value = "max.connections", defaultValue = "100")
    private Integer maxConnections;

    @HotValue(value = "allowed.ips", defaultValue = "127.0.0.1,localhost")
    private String[] allowedIps;

    @HotValue(value = "cache.ttl", defaultValue = "3600")
    private Long cacheTtl;

    @HotValue(value = "threshold", defaultValue = "0.85")
    private Double threshold;
}

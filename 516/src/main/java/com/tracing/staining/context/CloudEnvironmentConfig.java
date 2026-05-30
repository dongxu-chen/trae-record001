package com.tracing.staining.context;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "tracing.cloud")
public class CloudEnvironmentConfig {

    private String provider = "unknown";

    private String region = "unknown";

    private String availabilityZone = "unknown";

    private String accountId = "unknown";

    private String serviceName = "unknown";

    private boolean crossCloudEnabled = false;

    private String crossCloudTraceIdPrefix = "global";

    public boolean isCloudConfigured() {
        return !"unknown".equals(provider) && !"unknown".equals(region);
    }
}

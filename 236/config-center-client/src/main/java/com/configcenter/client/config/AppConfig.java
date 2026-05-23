package com.configcenter.client.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

@Data
@Component
@RefreshScope
@ConfigurationProperties(prefix = "app")
public class AppConfig {
    private String name = "default";
    private String version = "1.0.0";
    private String env = "dev";
    private Feature feature = new Feature();

    @Data
    public static class Feature {
        private boolean enableNewFeature = false;
        private int maxConnections = 100;
        private String theme = "light";
    }
}

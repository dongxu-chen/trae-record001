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

    private Feature feature = new Feature();
    private Threshold threshold = new Threshold();
    private Database database = new Database();

    @Data
    public static class Feature {
        private boolean enabled;
    }

    @Data
    public static class Threshold {
        private int maxRequests = 100;
        private int timeoutMs = 5000;
    }

    @Data
    public static class Database {
        private int maxConnections = 20;
        private int minIdle = 5;
    }
}

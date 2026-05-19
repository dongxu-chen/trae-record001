package com.configcenter.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

@Component
@RefreshScope
@ConfigurationProperties(prefix = "app")
public class AppConfig {

    private String name;
    private String version;
    private String environment;
    private Feature feature = new Feature();
    private Security security = new Security();

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getEnvironment() {
        return environment;
    }

    public void setEnvironment(String environment) {
        this.environment = environment;
    }

    public Feature getFeature() {
        return feature;
    }

    public void setFeature(Feature feature) {
        this.feature = feature;
    }

    public Security getSecurity() {
        return security;
    }

    public void setSecurity(Security security) {
        this.security = security;
    }

    public static class Feature {
        private boolean enableCache;
        private boolean enableLog;
        private int maxConnections;

        public boolean isEnableCache() {
            return enableCache;
        }

        public void setEnableCache(boolean enableCache) {
            this.enableCache = enableCache;
        }

        public boolean isEnableLog() {
            return enableLog;
        }

        public void setEnableLog(boolean enableLog) {
            this.enableLog = enableLog;
        }

        public int getMaxConnections() {
            return maxConnections;
        }

        public void setMaxConnections(int maxConnections) {
            this.maxConnections = maxConnections;
        }
    }

    public static class Security {
        private String apiKey;
        private String secretToken;

        public String getApiKey() {
            return apiKey;
        }

        public void setApiKey(String apiKey) {
            this.apiKey = apiKey;
        }

        public String getSecretToken() {
            return secretToken;
        }

        public void setSecretToken(String secretToken) {
            this.secretToken = secretToken;
        }
    }
}

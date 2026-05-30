package com.hotconfig.spring;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

@ConfigurationProperties(prefix = "hotconfig")
public class HotConfigProperties {

    private boolean enabled = true;

    private boolean enableApollo = false;

    private boolean enableFileWatch = true;

    private List<String> sources = new ArrayList<>();

    private List<String> fileSources = new ArrayList<>();

    private List<String> apolloNamespaces = new ArrayList<>();

    private String apolloAppId;

    private String apolloMetaServer;

    private boolean healthCheckEnabled = true;

    private boolean scheduledHealthCheckEnabled = false;

    private long healthCheckIntervalMs = 60000;

    private boolean failOnHealthCheckWarning = false;

    private boolean failOnHealthCheckError = false;

    private boolean rollbackEnabled = true;

    private boolean diffNotificationEnabled = true;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isEnableApollo() {
        return enableApollo;
    }

    public void setEnableApollo(boolean enableApollo) {
        this.enableApollo = enableApollo;
    }

    public boolean isEnableFileWatch() {
        return enableFileWatch;
    }

    public void setEnableFileWatch(boolean enableFileWatch) {
        this.enableFileWatch = enableFileWatch;
    }

    public List<String> getSources() {
        return sources;
    }

    public void setSources(List<String> sources) {
        this.sources = sources;
    }

    public List<String> getFileSources() {
        return fileSources;
    }

    public void setFileSources(List<String> fileSources) {
        this.fileSources = fileSources;
    }

    public List<String> getApolloNamespaces() {
        return apolloNamespaces;
    }

    public void setApolloNamespaces(List<String> apolloNamespaces) {
        this.apolloNamespaces = apolloNamespaces;
    }

    public String getApolloAppId() {
        return apolloAppId;
    }

    public void setApolloAppId(String apolloAppId) {
        this.apolloAppId = apolloAppId;
    }

    public String getApolloMetaServer() {
        return apolloMetaServer;
    }

    public void setApolloMetaServer(String apolloMetaServer) {
        this.apolloMetaServer = apolloMetaServer;
    }

    public boolean isHealthCheckEnabled() {
        return healthCheckEnabled;
    }

    public void setHealthCheckEnabled(boolean healthCheckEnabled) {
        this.healthCheckEnabled = healthCheckEnabled;
    }

    public boolean isScheduledHealthCheckEnabled() {
        return scheduledHealthCheckEnabled;
    }

    public void setScheduledHealthCheckEnabled(boolean scheduledHealthCheckEnabled) {
        this.scheduledHealthCheckEnabled = scheduledHealthCheckEnabled;
    }

    public long getHealthCheckIntervalMs() {
        return healthCheckIntervalMs;
    }

    public void setHealthCheckIntervalMs(long healthCheckIntervalMs) {
        this.healthCheckIntervalMs = healthCheckIntervalMs;
    }

    public boolean isFailOnHealthCheckWarning() {
        return failOnHealthCheckWarning;
    }

    public void setFailOnHealthCheckWarning(boolean failOnHealthCheckWarning) {
        this.failOnHealthCheckWarning = failOnHealthCheckWarning;
    }

    public boolean isFailOnHealthCheckError() {
        return failOnHealthCheckError;
    }

    public void setFailOnHealthCheckError(boolean failOnHealthCheckError) {
        this.failOnHealthCheckError = failOnHealthCheckError;
    }

    public boolean isRollbackEnabled() {
        return rollbackEnabled;
    }

    public void setRollbackEnabled(boolean rollbackEnabled) {
        this.rollbackEnabled = rollbackEnabled;
    }

    public boolean isDiffNotificationEnabled() {
        return diffNotificationEnabled;
    }

    public void setDiffNotificationEnabled(boolean diffNotificationEnabled) {
        this.diffNotificationEnabled = diffNotificationEnabled;
    }
}

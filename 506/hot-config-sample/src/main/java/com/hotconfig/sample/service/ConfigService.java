package com.hotconfig.sample.service;

import com.hotconfig.annotation.ConfigListener;
import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.sample.config.AppConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;

@Service
public class ConfigService {

    private static final Logger logger = LoggerFactory.getLogger(ConfigService.class);

    @Autowired
    private AppConfig appConfig;

    @Autowired
    private ConfigManager configManager;

    @HotValue(value = "custom.message", defaultValue = "Hello, Hot Config!")
    private String customMessage;

    @PostConstruct
    public void init() {
        logger.info("ConfigService initialized with customMessage: {}", customMessage);
        logger.info("AppConfig initial values: appName={}, version={}, env={}",
                appConfig.getAppName(), appConfig.getVersion(), appConfig.getEnv());
    }

    @ConfigListener(keys = {"app.name", "app.version"}, async = true)
    public void onAppConfigChange(ConfigChangeEvent event) {
        logger.info("Received app config change event from source: {}", event.getSourceName());
        event.getChanges().forEach((key, change) -> {
            logger.info("Config changed - key: {}, oldValue: {}, newValue: {}, type: {}",
                    key, change.getOldValue(), change.getNewValue(), change.getChangeType());
        });
        logger.info("Updated AppConfig values: appName={}, version={}",
                appConfig.getAppName(), appConfig.getVersion());
    }

    @ConfigListener(prefixes = {"app.feature", "app.connection"}, async = false)
    public void onFeatureConfigChange(ConfigChangeEvent event) {
        logger.info("Received feature/connection config change event");
        event.getChanges().forEach((key, change) -> {
            logger.info("Feature config changed - {}: {} -> {}",
                    key, change.getOldValue(), change.getNewValue());
        });
        logger.info("Feature toggle: {}, Connection timeout: {}",
                appConfig.getFeatureToggle(), appConfig.getConnectionTimeout());
    }

    @ConfigListener(sources = {"file"})
    public void onFileConfigChange(ConfigChangeEvent event) {
        logger.info("Received config change from FILE source: {}", event.getChangedKeys());
    }

    public void refreshConfig() {
        configManager.refresh();
        logger.info("Config refreshed manually");
    }

    public String getConfigValue(String key) {
        return configManager.getString(key);
    }

    public <T> T getConfigValue(String key, Class<T> type) {
        return configManager.getValue(key, type);
    }

    public void setLocalConfig(String key, Object value) {
        configManager.setLocalValue(key, value);
        logger.info("Set local config: {} = {}", key, value);
    }

    public AppConfig getAppConfig() {
        return appConfig;
    }

    public String getCustomMessage() {
        return customMessage;
    }
}

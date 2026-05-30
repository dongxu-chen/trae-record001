package com.hotconfig.sample.controller;

import com.hotconfig.sample.config.AppConfig;
import com.hotconfig.sample.service.ConfigService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config")
public class ConfigController {

    @Autowired
    private ConfigService configService;

    @GetMapping("/app")
    public AppConfig getAppConfig() {
        return configService.getAppConfig();
    }

    @GetMapping("/app/{field}")
    public Object getAppConfigField(@PathVariable String field) {
        AppConfig appConfig = configService.getAppConfig();
        switch (field) {
            case "appName":
                return appConfig.getAppName();
            case "version":
                return appConfig.getVersion();
            case "env":
                return appConfig.getEnv();
            case "featureToggle":
                return appConfig.getFeatureToggle();
            case "connectionTimeout":
                return appConfig.getConnectionTimeout();
            case "maxConnections":
                return appConfig.getMaxConnections();
            case "cacheTtl":
                return appConfig.getCacheTtl();
            case "threshold":
                return appConfig.getThreshold();
            case "allowedIps":
                return appConfig.getAllowedIps();
            default:
                return "Unknown field: " + field;
        }
    }

    @GetMapping("/value/{key}")
    public String getConfigValue(@PathVariable String key) {
        return configService.getConfigValue(key);
    }

    @GetMapping("/value/{key}/{type}")
    public Object getConfigValueTyped(@PathVariable String key, @PathVariable String type) {
        switch (type.toLowerCase()) {
            case "int":
            case "integer":
                return configService.getConfigValue(key, Integer.class);
            case "long":
                return configService.getConfigValue(key, Long.class);
            case "boolean":
                return configService.getConfigValue(key, Boolean.class);
            case "double":
                return configService.getConfigValue(key, Double.class);
            default:
                return configService.getConfigValue(key, String.class);
        }
    }

    @GetMapping("/custom-message")
    public String getCustomMessage() {
        return configService.getCustomMessage();
    }

    @PostMapping("/refresh")
    public Map<String, String> refreshConfig() {
        configService.refreshConfig();
        Map<String, String> result = new HashMap<>();
        result.put("status", "success");
        result.put("message", "Config refreshed successfully");
        return result;
    }

    @PostMapping("/local/{key}")
    public Map<String, String> setLocalConfig(@PathVariable String key, @RequestParam String value) {
        configService.setLocalConfig(key, value);
        Map<String, String> result = new HashMap<>();
        result.put("status", "success");
        result.put("key", key);
        result.put("value", value);
        return result;
    }

    @GetMapping("/snapshot")
    public Map<String, Object> getConfigSnapshot() {
        Map<String, Object> snapshot = new HashMap<>();
        AppConfig appConfig = configService.getAppConfig();

        snapshot.put("appName", appConfig.getAppName());
        snapshot.put("version", appConfig.getVersion());
        snapshot.put("env", appConfig.getEnv());
        snapshot.put("featureToggle", appConfig.getFeatureToggle());
        snapshot.put("connectionTimeout", appConfig.getConnectionTimeout());
        snapshot.put("maxConnections", appConfig.getMaxConnections());
        snapshot.put("cacheTtl", appConfig.getCacheTtl());
        snapshot.put("threshold", appConfig.getThreshold());
        snapshot.put("allowedIps", appConfig.getAllowedIps());
        snapshot.put("customMessage", configService.getCustomMessage());

        return snapshot;
    }
}

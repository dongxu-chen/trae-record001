package com.configcenter.client.controller;

import com.configcenter.client.config.AppConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config")
public class ConfigController {

    @Autowired
    private AppConfig appConfig;

    @GetMapping("/current")
    public Map<String, Object> getCurrentConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("feature", Map.of(
                "enabled", appConfig.getFeature().isEnabled()
        ));
        config.put("threshold", Map.of(
                "maxRequests", appConfig.getThreshold().getMaxRequests(),
                "timeoutMs", appConfig.getThreshold().getTimeoutMs()
        ));
        config.put("database", Map.of(
                "maxConnections", appConfig.getDatabase().getMaxConnections(),
                "minIdle", appConfig.getDatabase().getMinIdle()
        ));
        return config;
    }

    @GetMapping("/feature/enabled")
    public Map<String, Object> isFeatureEnabled() {
        return Map.of(
                "enabled", appConfig.getFeature().isEnabled()
        );
    }

    @GetMapping("/threshold")
    public Map<String, Object> getThreshold() {
        return Map.of(
                "maxRequests", appConfig.getThreshold().getMaxRequests(),
                "timeoutMs", appConfig.getThreshold().getTimeoutMs()
        );
    }

    @GetMapping("/database")
    public Map<String, Object> getDatabaseConfig() {
        return Map.of(
                "maxConnections", appConfig.getDatabase().getMaxConnections(),
                "minIdle", appConfig.getDatabase().getMinIdle()
        );
    }
}

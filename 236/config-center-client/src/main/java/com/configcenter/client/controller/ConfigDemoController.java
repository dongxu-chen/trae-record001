package com.configcenter.client.controller;

import com.configcenter.client.config.AppConfig;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RefreshScope
@RestController
@RequestMapping("/api")
public class ConfigDemoController {

    private final AppConfig appConfig;

    @Value("${app.name:default}")
    private String appName;

    @Value("${app.env:dev}")
    private String env;

    public ConfigDemoController(AppConfig appConfig) {
        this.appConfig = appConfig;
    }

    @GetMapping("/config")
    public Map<String, Object> getConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("appName", appName);
        config.put("env", env);
        config.put("appConfig", appConfig);
        return config;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        Map<String, String> result = new HashMap<>();
        result.put("status", "UP");
        result.put("app", appName);
        result.put("env", env);
        return result;
    }
}

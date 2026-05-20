package com.configcenter.controller;

import com.configcenter.config.AppConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config")
@RefreshScope
public class ConfigController {

    @Autowired
    private AppConfig appConfig;

    @Value("${app.message:default message}")
    private String message;

    @Value("${spring.profiles.active:default}")
    private String activeProfile;

    @Value("${spring.datasource.password:not set}")
    private String dbPassword;

    @GetMapping
    public Map<String, Object> getConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("appName", appConfig.getName());
        config.put("version", appConfig.getVersion());
        config.put("environment", appConfig.getEnvironment());
        config.put("message", message);
        config.put("activeProfile", activeProfile);

        Map<String, Object> features = new HashMap<>();
        features.put("enableCache", appConfig.getFeature().isEnableCache());
        features.put("enableLog", appConfig.getFeature().isEnableLog());
        features.put("maxConnections", appConfig.getFeature().getMaxConnections());
        config.put("features", features);

        Map<String, Object> security = new HashMap<>();
        security.put("apiKey", maskValue(appConfig.getSecurity().getApiKey()));
        security.put("secretToken", maskValue(appConfig.getSecurity().getSecretToken()));
        security.put("dbPassword", maskValue(dbPassword));
        security.put("encryptionStatus", "DECRYPTED");
        config.put("security", security);

        return config;
    }

    @GetMapping("/message")
    public String getMessage() {
        return message;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        Map<String, String> result = new HashMap<>();
        result.put("status", "UP");
        result.put("service", "config-client");
        return result;
    }

    @GetMapping("/encryption-status")
    public Map<String, Object> getEncryptionStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("status", "OK");
        status.put("encryption", "JASYPT");
        status.put("decryptionEnabled", true);
        status.put("apiKeyDecrypted", appConfig.getSecurity().getApiKey() != null);
        return status;
    }

    private String maskValue(String value) {
        if (value == null || value.length() <= 4) {
            return "****";
        }
        return value.substring(0, 2) + "****" + value.substring(value.length() - 2);
    }
}

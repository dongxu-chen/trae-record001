package com.configcenter.example.controller;

import com.configcenter.client.ConfigServiceClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 配置测试控制器
 */
@RestController
@RequestMapping("/api/config")
public class ConfigTestController {

    @Autowired(required = false)
    private ConfigServiceClient configServiceClient;

    // 演示通过@Value注入配置
    @Value("${app.name:default-app}")
    private String appName;

    @Value("${app.version:1.0.0}")
    private String appVersion;

    @Value("${app.env:dev}")
    private String appEnv;

    @Value("${app.feature.enabled:false}")
    private boolean featureEnabled;

    /**
     * 获取配置信息
     */
    @GetMapping
    public Map<String, Object> getConfig() {
        Map<String, Object> result = new HashMap<>();
        result.put("appName", appName);
        result.put("appVersion", appVersion);
        result.put("appEnv", appEnv);
        result.put("featureEnabled", featureEnabled);

        if (configServiceClient != null) {
            result.put("clientId", configServiceClient.getClientId());
            result.put("connected", configServiceClient.isConnected());
            result.put("allConfigs", configServiceClient.getAllConfigs());
        }

        return result;
    }

    /**
     * 获取指定配置
     */
    @GetMapping("/{key}")
    public Map<String, Object> getConfigByKey(@PathVariable String key) {
        Map<String, Object> result = new HashMap<>();
        result.put("key", key);

        if (configServiceClient != null) {
            result.put("value", configServiceClient.getConfig(key));
        }

        return result;
    }

    /**
     * 主动拉取配置
     */
    @PostMapping("/pull/{dataId}")
    public Map<String, Object> pullConfig(@PathVariable String dataId,
                                           @RequestParam(defaultValue = "false") boolean fullPull) {
        Map<String, Object> result = new HashMap<>();

        if (configServiceClient != null) {
            Map<String, String> config = configServiceClient.pullConfig(dataId, fullPull);
            result.put("pulledConfig", config);
            result.put("pulledCount", config.size());
        } else {
            result.put("error", "ConfigServiceClient not available");
        }

        return result;
    }

    /**
     * 健康检查
     */
    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("service", "config-center-example");

        if (configServiceClient != null) {
            result.put("clientConnected", configServiceClient.isConnected());
        }

        return result;
    }
}

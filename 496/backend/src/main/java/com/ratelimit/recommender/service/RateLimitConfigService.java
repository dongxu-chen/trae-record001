package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class RateLimitConfigService {

    private final Map<String, RateLimitConfig> configStore = new ConcurrentHashMap<>();

    public RateLimitConfig applyRecommendation(RateLimitRecommendation recommendation) {
        RateLimitConfig config = RateLimitConfig.builder()
                .serviceId(recommendation.getServiceId())
                .serviceLevelRule(recommendation.getRecommendedServiceRule())
                .apiLevelRules(recommendation.getRecommendedApiRules())
                .enabled(true)
                .strategy("AUTO_RECOMMENDED")
                .createTime(LocalDateTime.now())
                .updateTime(LocalDateTime.now())
                .build();

        configStore.put(recommendation.getServiceId(), config);
        return config;
    }

    public RateLimitConfig getConfig(String serviceId) {
        return configStore.get(serviceId);
    }

    public Map<String, RateLimitConfig> getAllConfigs() {
        return new ConcurrentHashMap<>(configStore);
    }

    public RateLimitConfig updateConfig(String serviceId, RateLimitConfig config) {
        config.setServiceId(serviceId);
        config.setUpdateTime(LocalDateTime.now());
        configStore.put(serviceId, config);
        return config;
    }

    public boolean deleteConfig(String serviceId) {
        return configStore.remove(serviceId) != null;
    }

    public RateLimitConfig toggleConfig(String serviceId, boolean enabled) {
        RateLimitConfig config = configStore.get(serviceId);
        if (config != null) {
            config.setEnabled(enabled);
            config.setUpdateTime(LocalDateTime.now());
        }
        return config;
    }

    public String exportConfigAsYaml(String serviceId) {
        RateLimitConfig config = configStore.get(serviceId);
        if (config == null) {
            return "";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("rateLimit:\n");
        sb.append("  service: ").append(serviceId).append("\n");
        sb.append("  enabled: ").append(config.isEnabled()).append("\n");
        sb.append("  serviceLevel:\n");
        sb.append("    qps: ").append(config.getServiceLevelRule().getQpsThreshold()).append("\n");
        sb.append("    burst: ").append(config.getServiceLevelRule().getBurstCapacity()).append("\n");
        sb.append("  apiLevel:\n");

        for (Map.Entry<String, RateLimitRule> entry : config.getApiLevelRules().entrySet()) {
            sb.append("    ").append(entry.getKey()).append(":\n");
            sb.append("      qps: ").append(entry.getValue().getQpsThreshold()).append("\n");
            sb.append("      burst: ").append(entry.getValue().getBurstCapacity()).append("\n");
        }

        return sb.toString();
    }
}

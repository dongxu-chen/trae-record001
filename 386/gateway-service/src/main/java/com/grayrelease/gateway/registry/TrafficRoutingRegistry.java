package com.grayrelease.gateway.registry;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class TrafficRoutingRegistry {

    private final Map<String, RoutingConfig> routingConfigs = new ConcurrentHashMap<>();

    public void updateRouting(String serviceName, RoutingConfig config) {
        routingConfigs.put(serviceName, config);
        log.info("Routing updated: service={}, stable={}, canary={}, weight={}%",
                serviceName, config.getStableVersion(), config.getCanaryVersion(), config.getCanaryWeight());
    }

    public RoutingConfig getRouting(String serviceName) {
        return routingConfigs.get(serviceName);
    }

    public Map<String, RoutingConfig> getAllRoutings() {
        return new ConcurrentHashMap<>(routingConfigs);
    }

    public void removeRouting(String serviceName) {
        routingConfigs.remove(serviceName);
        log.info("Routing removed: service={}", serviceName);
    }

    @Data
    public static class RoutingConfig {
        private String serviceName;
        private String stableVersion;
        private String canaryVersion;
        private int canaryWeight;
        private String stableHost;
        private int stablePort;
        private String canaryHost;
        private int canaryPort;
        private Map<String, String> matchRules;
    }
}
package com.grayrelease.release.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class TrafficRouterRegistry {

    private static final Map<String, String> routingRules = new ConcurrentHashMap<>();

    public static void updateRouting(String rule) {
        routingRules.put("default", rule);
        log.debug("Routing rule updated in registry: {}", rule);
    }

    public static String getRouting(String serviceName) {
        return routingRules.get(serviceName);
    }

    public static Map<String, String> getAllRoutings() {
        return new ConcurrentHashMap<>(routingRules);
    }

    public static void clear() {
        routingRules.clear();
    }
}
package com.migration.traffic;

import com.migration.engine.DualDiscoveryEngine;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class TrafficRouter {

    private final DualDiscoveryEngine discoveryEngine;
    private final Map<String, GrayscaleStrategy> strategies = new ConcurrentHashMap<>();

    public TrafficRouter(DualDiscoveryEngine discoveryEngine) {
        this.discoveryEngine = discoveryEngine;
    }

    public GrayscaleStrategy setTrafficRatio(String serviceId, double nacosRatio) {
        if (nacosRatio < 0.0 || nacosRatio > 1.0) {
            throw new IllegalArgumentException("Nacos ratio must be between 0.0 and 1.0");
        }

        GrayscaleStrategy strategy = strategies.get(serviceId);
        if (strategy == null) {
            strategy = new GrayscaleStrategy(serviceId, nacosRatio);
            strategies.put(serviceId, strategy);
        } else {
            strategy.setNacosTrafficRatio(nacosRatio);
        }

        discoveryEngine.setServiceTrafficRatio(serviceId, nacosRatio);

        if (strategy.isAllNacos()) {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.NACOS_ONLY);
        } else if (strategy.isAllEureka()) {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.EUREKA_ONLY);
        } else {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_BALANCED);
        }

        log.info("Set traffic ratio for service {}: {}% Nacos, {}% Eureka",
                serviceId, strategy.getNacosPercentage(), 100 - strategy.getNacosPercentage());

        return strategy;
    }

    public GrayscaleStrategy setTrafficPercentage(String serviceId, int nacosPercentage) {
        if (nacosPercentage < 0 || nacosPercentage > 100) {
            throw new IllegalArgumentException("Nacos percentage must be between 0 and 100");
        }
        return setTrafficRatio(serviceId, nacosPercentage / 100.0);
    }

    public void setGlobalTrafficRatio(double nacosRatio) {
        for (String serviceId : discoveryEngine.discoverAll().keySet()) {
            setTrafficRatio(serviceId, nacosRatio);
        }
        log.info("Set global traffic ratio: {}% Nacos", (int) (nacosRatio * 100));
    }

    public void setGlobalTrafficPercentage(int nacosPercentage) {
        setGlobalTrafficRatio(nacosPercentage / 100.0);
    }

    public GrayscaleStrategy getStrategy(String serviceId) {
        return strategies.get(serviceId);
    }

    public Map<String, GrayscaleStrategy> getAllStrategies() {
        return Collections.unmodifiableMap(strategies);
    }

    public void removeStrategy(String serviceId) {
        strategies.remove(serviceId);
        log.info("Removed traffic strategy for service {}", serviceId);
    }

    public ServiceInstance route(String serviceId) {
        GrayscaleStrategy strategy = strategies.get(serviceId);

        if (strategy == null || strategy.isAllEureka()) {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.EUREKA_ONLY);
            List<ServiceInstance> instances = discoveryEngine.discover(serviceId);
            return selectInstance(instances);
        }

        if (strategy.isAllNacos()) {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.NACOS_ONLY);
            List<ServiceInstance> instances = discoveryEngine.discover(serviceId);
            return selectInstance(instances);
        }

        if (strategy.shouldRouteToNacos()) {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_PREFER_NACOS);
        } else {
            discoveryEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_PREFER_EUREKA);
        }

        List<ServiceInstance> instances = discoveryEngine.discover(serviceId);
        return selectInstance(instances);
    }

    public void fullSwitchToNacos(String serviceId) {
        setTrafficRatio(serviceId, 1.0);
        log.info("Service {} fully switched to Nacos", serviceId);
    }

    public void fullSwitchToEureka(String serviceId) {
        setTrafficRatio(serviceId, 0.0);
        log.info("Service {} fully switched to Eureka", serviceId);
    }

    public void fullGlobalSwitchToNacos() {
        setGlobalTrafficRatio(1.0);
        log.info("All services fully switched to Nacos");
    }

    public void fullGlobalSwitchToEureka() {
        setGlobalTrafficRatio(0.0);
        log.info("All services fully switched to Eureka");
    }

    public Map<String, Object> getTrafficStatus(String serviceId) {
        GrayscaleStrategy strategy = strategies.get(serviceId);
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("serviceId", serviceId);

        if (strategy == null) {
            status.put("status", "NO_STRATEGY");
            status.put("nacosPercentage", 0);
            status.put("eurekaPercentage", 100);
            status.put("description", "No traffic strategy configured, using Eureka only");
        } else {
            status.put("status", "ACTIVE");
            status.put("nacosPercentage", strategy.getNacosPercentage());
            status.put("eurekaPercentage", 100 - strategy.getNacosPercentage());
            status.put("description", strategy.getStatusDescription());
        }

        return status;
    }

    public Map<String, Map<String, Object>> getAllTrafficStatus() {
        Map<String, Map<String, Object>> allStatus = new LinkedHashMap<>();
        for (String serviceId : discoveryEngine.discoverAll().keySet()) {
            allStatus.put(serviceId, getTrafficStatus(serviceId));
        }
        for (Map.Entry<String, GrayscaleStrategy> entry : strategies.entrySet()) {
            if (!allStatus.containsKey(entry.getKey())) {
                allStatus.put(entry.getKey(), getTrafficStatus(entry.getKey()));
            }
        }
        return allStatus;
    }

    private ServiceInstance selectInstance(List<ServiceInstance> instances) {
        if (instances == null || instances.isEmpty()) {
            return null;
        }
        return instances.get(new Random().nextInt(instances.size()));
    }
}

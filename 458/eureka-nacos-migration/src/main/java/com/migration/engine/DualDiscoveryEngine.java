package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
public class DualDiscoveryEngine {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;

    private DiscoveryMode currentMode = DiscoveryMode.EUREKA_ONLY;

    private final Map<String, Double> serviceTrafficRatio = new ConcurrentHashMap<>();

    public DualDiscoveryEngine(EurekaClient eurekaClient, NacosClient nacosClient) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
    }

    public enum DiscoveryMode {
        EUREKA_ONLY,
        NACOS_ONLY,
        DUAL_PREFER_EUREKA,
        DUAL_PREFER_NACOS,
        DUAL_BALANCED
    }

    public List<ServiceInstance> discover(String serviceId) {
        switch (currentMode) {
            case EUREKA_ONLY:
                return eurekaClient.getInstances(serviceId);
            case NACOS_ONLY:
                return nacosClient.getInstances(serviceId);
            case DUAL_PREFER_EUREKA:
                return discoverDualPreferEureka(serviceId);
            case DUAL_PREFER_NACOS:
                return discoverDualPreferNacos(serviceId);
            case DUAL_BALANCED:
                return discoverDualBalanced(serviceId);
            default:
                return eurekaClient.getInstances(serviceId);
        }
    }

    public Map<String, List<ServiceInstance>> discoverAll() {
        Map<String, List<ServiceInstance>> result = new HashMap<>();

        List<String> eurekaServices = eurekaClient.getAllServiceIds();
        List<String> nacosServices = nacosClient.getAllServiceIds();

        Set<String> allServiceIds = new HashSet<>();
        allServiceIds.addAll(eurekaServices);
        allServiceIds.addAll(nacosServices);

        for (String serviceId : allServiceIds) {
            result.put(serviceId, discover(serviceId));
        }

        return result;
    }

    public void setMode(DiscoveryMode mode) {
        this.currentMode = mode;
        log.info("Discovery mode changed to {}", mode);
    }

    public DiscoveryMode getMode() {
        return currentMode;
    }

    public void setServiceTrafficRatio(String serviceId, double nacosRatio) {
        serviceTrafficRatio.put(serviceId, nacosRatio);
        log.info("Set Nacos traffic ratio for {} to {}", serviceId, nacosRatio);
    }

    public Map<String, List<ServiceInstance>> getEurekaSnapshot() {
        List<String> serviceIds = eurekaClient.getAllServiceIds();
        Map<String, List<ServiceInstance>> snapshot = new HashMap<>();
        for (String serviceId : serviceIds) {
            snapshot.put(serviceId, eurekaClient.getInstances(serviceId));
        }
        return snapshot;
    }

    public Map<String, List<ServiceInstance>> getNacosSnapshot() {
        List<String> serviceIds = nacosClient.getAllServiceIds();
        Map<String, List<ServiceInstance>> snapshot = new HashMap<>();
        for (String serviceId : serviceIds) {
            snapshot.put(serviceId, nacosClient.getInstances(serviceId));
        }
        return snapshot;
    }

    private List<ServiceInstance> discoverDualPreferEureka(String serviceId) {
        List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
        if (!eurekaInstances.isEmpty()) {
            return eurekaInstances;
        }
        log.warn("Eureka returned no instances for {}, falling back to Nacos", serviceId);
        return nacosClient.getInstances(serviceId);
    }

    private List<ServiceInstance> discoverDualPreferNacos(String serviceId) {
        List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);
        if (!nacosInstances.isEmpty()) {
            return nacosInstances;
        }
        log.warn("Nacos returned no instances for {}, falling back to Eureka", serviceId);
        return eurekaClient.getInstances(serviceId);
    }

    private List<ServiceInstance> discoverDualBalanced(String serviceId) {
        Double ratio = serviceTrafficRatio.getOrDefault(serviceId, 0.5);
        List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
        List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);

        if (eurekaInstances.isEmpty()) return nacosInstances;
        if (nacosInstances.isEmpty()) return eurekaInstances;

        int nacosCount = (int) Math.round(nacosInstances.size() * ratio);
        int eurekaCount = eurekaInstances.size() - nacosCount;
        if (eurekaCount < 0) eurekaCount = 0;

        List<ServiceInstance> merged = new ArrayList<>();
        if (eurekaCount > 0) {
            merged.addAll(eurekaInstances.stream().limit(eurekaCount).collect(Collectors.toList()));
        }
        merged.addAll(nacosInstances.stream().limit(Math.max(nacosCount, 1)).collect(Collectors.toList()));

        return merged;
    }
}

package com.migration.client;

import com.alibaba.nacos.api.exception.NacosException;
import com.alibaba.nacos.api.naming.NamingFactory;
import com.alibaba.nacos.api.naming.NamingService;
import com.alibaba.nacos.api.naming.pojo.Instance;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class NacosClient {

    private NamingService namingService;

    @Value("${nacos.server-addr}")
    private String serverAddr;

    @Value("${nacos.namespace}")
    private String namespace;

    @Value("${nacos.group}")
    private String group;

    @Value("${nacos.username}")
    private String username;

    @Value("${nacos.password}")
    private String password;

    @PostConstruct
    public void init() {
        try {
            Properties properties = new Properties();
            properties.put("serverAddr", serverAddr);
            properties.put("namespace", namespace);
            properties.put("username", username);
            properties.put("password", password);
            namingService = NamingFactory.createNamingService(properties);
            log.info("Nacos NamingService initialized, serverAddr={}", serverAddr);
        } catch (NacosException e) {
            log.error("Failed to initialize Nacos NamingService", e);
        }
    }

    @PreDestroy
    public void destroy() {
        if (namingService != null) {
            try {
                namingService.shutDown();
            } catch (NacosException e) {
                log.warn("Error shutting down Nacos NamingService", e);
            }
        }
    }

    public List<String> getAllServiceIds() {
        try {
            return namingService.getServicesOfServer(1, Integer.MAX_VALUE, group)
                    .getData();
        } catch (NacosException e) {
            log.error("Failed to fetch service IDs from Nacos", e);
            return Collections.emptyList();
        }
    }

    public List<ServiceInstance> getInstances(String serviceId) {
        try {
            List<Instance> nacosInstances = namingService.selectInstances(serviceId, group, true);
            return nacosInstances.stream()
                    .map(this::convertToServiceInstance)
                    .collect(Collectors.toList());
        } catch (NacosException e) {
            log.error("Failed to fetch instances for service {} from Nacos", serviceId, e);
            return Collections.emptyList();
        }
    }

    public List<ServiceInstance> getAllInstances() {
        List<String> serviceIds = getAllServiceIds();
        List<ServiceInstance> allInstances = new ArrayList<>();
        for (String serviceId : serviceIds) {
            allInstances.addAll(getInstances(serviceId));
        }
        return allInstances;
    }

    public boolean registerInstance(ServiceInstance instance) {
        try {
            Instance nacosInstance = convertToNacosInstance(instance);
            namingService.registerInstance(instance.getServiceId(), group, nacosInstance);
            log.info("Registered instance {} in Nacos", instance.getInstanceId());
            return true;
        } catch (NacosException e) {
            log.error("Failed to register instance {} in Nacos", instance.getInstanceId(), e);
            return false;
        }
    }

    public boolean deregisterInstance(ServiceInstance instance) {
        try {
            Instance nacosInstance = convertToNacosInstance(instance);
            namingService.deregisterInstance(instance.getServiceId(), group, nacosInstance);
            log.info("Deregistered instance {} from Nacos", instance.getInstanceId());
            return true;
        } catch (NacosException e) {
            log.error("Failed to deregister instance {} from Nacos", instance.getInstanceId(), e);
            return false;
        }
    }

    public boolean sendHeartbeat(ServiceInstance instance) {
        try {
            List<Instance> instances = namingService.selectInstances(instance.getServiceId(), group, true);
            boolean healthy = instances.stream()
                    .anyMatch(i -> i.getIp().equals(instance.getHost()) && i.getPort() == instance.getPort());
            if (!healthy) {
                Instance nacosInstance = convertToNacosInstance(instance);
                namingService.registerInstance(instance.getServiceId(), group, nacosInstance);
                log.info("Re-registered instance {} in Nacos (heartbeat recovery)", instance.getInstanceId());
            }
            return true;
        } catch (NacosException e) {
            log.warn("Heartbeat check failed for {} in Nacos", instance.getInstanceId());
            return false;
        }
    }

    public boolean isAvailable() {
        try {
            return namingService != null && namingService.getServerStatus().equals("UP");
        } catch (Exception e) {
            return false;
        }
    }

    private ServiceInstance convertToServiceInstance(Instance nacosInstance) {
        return ServiceInstance.builder()
                .serviceId(nacosInstance.getServiceName())
                .instanceId(nacosInstance.getInstanceId())
                .host(nacosInstance.getIp())
                .port(nacosInstance.getPort())
                .scheme("http")
                .status(nacosInstance.isHealthy() ? "UP" : "DOWN")
                .metadata(nacosInstance.getMetadata() != null ? nacosInstance.getMetadata() : new HashMap<>())
                .registrySource("NACOS")
                .build();
    }

    private Instance convertToNacosInstance(ServiceInstance instance) {
        Instance nacosInstance = new Instance();
        nacosInstance.setIp(instance.getHost());
        nacosInstance.setPort(instance.getPort());
        nacosInstance.setServiceName(instance.getServiceId());
        nacosInstance.setInstanceId(instance.getInstanceId());
        nacosInstance.setHealthy(true);
        nacosInstance.setEnabled(true);
        nacosInstance.setWeight(1.0);
        if (instance.getMetadata() != null) {
            nacosInstance.setMetadata(instance.getMetadata());
        } else {
            nacosInstance.setMetadata(new HashMap<>());
        }
        nacosInstance.getMetadata().put("migratedFrom", "eureka");
        nacosInstance.getMetadata().put("migratedAt", String.valueOf(System.currentTimeMillis()));
        return nacosInstance;
    }
}

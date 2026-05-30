package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.config.MigrationProperties;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.*;

@Slf4j
@Component
public class DualRegistrationEngine {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final MigrationProperties properties;
    private final ScheduledExecutorService heartbeatExecutor;
    private final ConcurrentMap<String, ServiceInstance> dualRegisteredServices = new ConcurrentHashMap<>();

    public DualRegistrationEngine(EurekaClient eurekaClient,
                                   NacosClient nacosClient,
                                   MigrationProperties properties) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
        this.properties = properties;
        this.heartbeatExecutor = Executors.newScheduledThreadPool(2);
    }

    public boolean dualRegister(ServiceInstance instance) {
        boolean eurekaOk = eurekaClient.registerInstance(instance);
        boolean nacosOk = nacosClient.registerInstance(instance);

        if (eurekaOk && nacosOk) {
            dualRegisteredServices.put(instance.getInstanceId(), instance);
            log.info("Dual registration successful for instance {}", instance.getInstanceId());
            return true;
        }

        if (eurekaOk && !nacosOk) {
            log.warn("Eureka registered but Nacos failed for {}, rolling back Eureka registration",
                    instance.getInstanceId());
            eurekaClient.deregisterInstance(instance.getServiceId(), instance.getInstanceId());
            return false;
        }

        if (!eurekaOk && nacosOk) {
            log.warn("Nacos registered but Eureka failed for {}, rolling back Nacos registration",
                    instance.getInstanceId());
            nacosClient.deregisterInstance(instance);
            return false;
        }

        log.error("Both registrations failed for instance {}", instance.getInstanceId());
        return false;
    }

    public int dualRegisterBatch(List<ServiceInstance> instances) {
        int successCount = 0;
        for (ServiceInstance instance : instances) {
            if (dualRegister(instance)) {
                successCount++;
            }
        }
        log.info("Batch dual registration: {}/{} instances registered", successCount, instances.size());
        return successCount;
    }

    public void startDualHeartbeat() {
        heartbeatExecutor.scheduleAtFixedRate(this::sendDualHeartbeats,
                0, properties.getHeartbeatIntervalMs(), TimeUnit.MILLISECONDS);
        log.info("Dual heartbeat started with interval {}ms", properties.getHeartbeatIntervalMs());
    }

    public void stopDualHeartbeat() {
        heartbeatExecutor.shutdown();
        try {
            if (!heartbeatExecutor.awaitTermination(10, TimeUnit.SECONDS)) {
                heartbeatExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            heartbeatExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
        log.info("Dual heartbeat stopped");
    }

    private void sendDualHeartbeats() {
        for (ServiceInstance instance : dualRegisteredServices.values()) {
            boolean eurekaBeat = eurekaClient.sendHeartbeat(instance.getServiceId(), instance.getInstanceId());
            boolean nacosBeat = nacosClient.sendHeartbeat(instance);

            if (!eurekaBeat) {
                log.warn("Eureka heartbeat failed for {}", instance.getInstanceId());
            }
            if (!nacosBeat) {
                log.warn("Nacos heartbeat failed for {}", instance.getInstanceId());
            }
        }
    }

    public boolean deregisterFromNacos(ServiceInstance instance) {
        boolean result = nacosClient.deregisterInstance(instance);
        if (result) {
            dualRegisteredServices.remove(instance.getInstanceId());
            log.info("Deregistered from Nacos: {}", instance.getInstanceId());
        }
        return result;
    }

    public boolean deregisterFromEureka(ServiceInstance instance) {
        boolean result = eurekaClient.deregisterInstance(instance.getServiceId(), instance.getInstanceId());
        if (result) {
            dualRegisteredServices.remove(instance.getInstanceId());
            log.info("Deregistered from Eureka: {}", instance.getInstanceId());
        }
        return result;
    }

    public int deregisterAllFromNacos() {
        int count = 0;
        for (ServiceInstance instance : dualRegisteredServices.values()) {
            if (nacosClient.deregisterInstance(instance)) {
                count++;
            }
        }
        dualRegisteredServices.clear();
        log.info("Deregistered {} instances from Nacos", count);
        return count;
    }

    public int deregisterAllFromEureka() {
        int count = 0;
        for (ServiceInstance instance : dualRegisteredServices.values()) {
            if (eurekaClient.deregisterInstance(instance.getServiceId(), instance.getInstanceId())) {
                count++;
            }
        }
        dualRegisteredServices.clear();
        log.info("Deregistered {} instances from Eureka", count);
        return count;
    }

    public ConcurrentMap<String, ServiceInstance> getDualRegisteredServices() {
        return dualRegisteredServices;
    }
}

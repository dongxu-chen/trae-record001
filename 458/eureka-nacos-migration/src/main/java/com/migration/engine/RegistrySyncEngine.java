package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.config.MigrationProperties;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class RegistrySyncEngine {

    public enum SyncDirection {
        EUREKA_TO_NACOS,
        NACOS_TO_EUREKA,
        BIDIRECTIONAL
    }

    public enum SyncMode {
        MANUAL,
        AUTO
    }

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final MigrationProperties properties;
    private final ScheduledExecutorService syncExecutor;
    private ScheduledFuture<?> syncTask;

    private SyncDirection syncDirection = SyncDirection.EUREKA_TO_NACOS;
    private SyncMode syncMode = SyncMode.MANUAL;
    private volatile boolean syncRunning = false;

    private final ConcurrentMap<String, ServiceInstance> syncedInstances = new ConcurrentHashMap<>();
    private final List<SyncRecord> syncHistory = Collections.synchronizedList(new ArrayList<>());

    public RegistrySyncEngine(EurekaClient eurekaClient,
                               NacosClient nacosClient,
                               MigrationProperties properties) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
        this.properties = properties;
        this.syncExecutor = Executors.newScheduledThreadPool(2);
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class SyncRecord {
        private String syncId;
        private SyncDirection direction;
        private long timestamp;
        private int syncedCount;
        private int skippedCount;
        private int failedCount;
        private List<String> failedInstances;
    }

    public SyncRecord syncOnce() {
        return syncOnce(syncDirection);
    }

    public SyncRecord syncOnce(SyncDirection direction) {
        String syncId = UUID.randomUUID().toString();
        long startTime = System.currentTimeMillis();
        int syncedCount = 0;
        int skippedCount = 0;
        int failedCount = 0;
        List<String> failedInstances = new ArrayList<>();

        log.info("[{}] Starting one-time sync, direction: {}", syncId, direction);

        try {
            if (direction == SyncDirection.EUREKA_TO_NACOS || direction == SyncDirection.BIDIRECTIONAL) {
                SyncResult result = syncFromSourceToTarget(
                        () -> eurekaClient.getAllServiceIds().stream()
                                .flatMap(id -> eurekaClient.getInstances(id).stream())
                                .collect(Collectors.toList()),
                        instance -> nacosClient.registerInstance(instance),
                        instance -> nacosClient.getInstances(instance.getServiceId()).stream()
                                .anyMatch(i -> i.getHost().equals(instance.getHost()) && i.getPort() == instance.getPort())
                );
                syncedCount += result.synced;
                skippedCount += result.skipped;
                failedCount += result.failed;
                failedInstances.addAll(result.failedInstances);
            }

            if (direction == SyncDirection.NACOS_TO_EUREKA || direction == SyncDirection.BIDIRECTIONAL) {
                SyncResult result = syncFromSourceToTarget(
                        () -> nacosClient.getAllServiceIds().stream()
                                .flatMap(id -> nacosClient.getInstances(id).stream())
                                .collect(Collectors.toList()),
                        instance -> eurekaClient.registerInstance(instance),
                        instance -> eurekaClient.getInstances(instance.getServiceId()).stream()
                                .anyMatch(i -> i.getHost().equals(instance.getHost()) && i.getPort() == instance.getPort())
                );
                syncedCount += result.synced;
                skippedCount += result.skipped;
                failedCount += result.failed;
                failedInstances.addAll(result.failedInstances);
            }

            syncedInstances.clear();
            Map<String, List<ServiceInstance>> eurekaMap = buildInstanceMap(eurekaClient.getAllInstances());
            Map<String, List<ServiceInstance>> nacosMap = buildInstanceMap(nacosClient.getAllInstances());

            for (Map.Entry<String, List<ServiceInstance>> entry : eurekaMap.entrySet()) {
                for (ServiceInstance inst : entry.getValue()) {
                    syncedInstances.put(inst.getInstanceId(), inst);
                }
            }
            for (Map.Entry<String, List<ServiceInstance>> entry : nacosMap.entrySet()) {
                for (ServiceInstance inst : entry.getValue()) {
                    syncedInstances.putIfAbsent(inst.getInstanceId(), inst);
                }
            }

        } catch (Exception e) {
            log.error("[{}] Sync failed", syncId, e);
        }

        long elapsed = System.currentTimeMillis() - startTime;
        SyncRecord record = SyncRecord.builder()
                .syncId(syncId)
                .direction(direction)
                .timestamp(startTime)
                .syncedCount(syncedCount)
                .skippedCount(skippedCount)
                .failedCount(failedCount)
                .failedInstances(failedInstances)
                .build();
        syncHistory.add(record);

        log.info("[{}] Sync completed in {}ms: synced={}, skipped={}, failed={}",
                syncId, elapsed, syncedCount, skippedCount, failedCount);
        if (!failedInstances.isEmpty()) {
            log.warn("[{}] Failed instances: {}", syncId, failedInstances);
        }

        return record;
    }

    public synchronized void startAutoSync() {
        if (syncRunning) {
            log.warn("Auto sync is already running");
            return;
        }
        syncMode = SyncMode.AUTO;
        syncRunning = true;
        syncTask = syncExecutor.scheduleAtFixedRate(
                this::syncOnce,
                0,
                properties.getHeartbeatIntervalMs(),
                TimeUnit.MILLISECONDS
        );
        log.info("Auto sync started with interval {}ms, direction: {}", properties.getHeartbeatIntervalMs(), syncDirection);
    }

    public synchronized void stopAutoSync() {
        if (!syncRunning) {
            log.warn("Auto sync is not running");
            return;
        }
        syncRunning = false;
        syncMode = SyncMode.MANUAL;
        if (syncTask != null) {
            syncTask.cancel(false);
        }
        log.info("Auto sync stopped");
    }

    public Map<String, List<ServiceInstance>> getConsolidatedInstanceList() {
        Map<String, List<ServiceInstance>> eurekaMap = buildInstanceMap(eurekaClient.getAllInstances());
        Map<String, List<ServiceInstance>> nacosMap = buildInstanceMap(nacosClient.getAllInstances());

        Set<String> allServiceIds = new HashSet<>();
        allServiceIds.addAll(eurekaMap.keySet());
        allServiceIds.addAll(nacosMap.keySet());

        Map<String, List<ServiceInstance>> result = new LinkedHashMap<>();
        for (String serviceId : allServiceIds) {
            List<ServiceInstance> merged = new ArrayList<>();
            Map<String, ServiceInstance> instanceMap = new LinkedHashMap<>();

            List<ServiceInstance> eurekaInsts = eurekaMap.getOrDefault(serviceId, Collections.emptyList());
            for (ServiceInstance inst : eurekaInsts) {
                String key = inst.getHost() + ":" + inst.getPort();
                instanceMap.put(key, inst);
            }

            List<ServiceInstance> nacosInsts = nacosMap.getOrDefault(serviceId, Collections.emptyList());
            for (ServiceInstance inst : nacosInsts) {
                String key = inst.getHost() + ":" + inst.getPort();
                if (!instanceMap.containsKey(key)) {
                    instanceMap.put(key, inst);
                }
            }

            merged.addAll(instanceMap.values());
            result.put(serviceId, merged);
        }
        return result;
    }

    public void setSyncDirection(SyncDirection direction) {
        this.syncDirection = direction;
        log.info("Sync direction changed to {}", direction);
    }

    public SyncDirection getSyncDirection() {
        return syncDirection;
    }

    public SyncMode getSyncMode() {
        return syncMode;
    }

    public boolean isSyncRunning() {
        return syncRunning;
    }

    public List<SyncRecord> getSyncHistory() {
        return Collections.unmodifiableList(syncHistory);
    }

    public ConcurrentMap<String, ServiceInstance> getSyncedInstances() {
        return syncedInstances;
    }

    public int deregisterAllFromNacos() {
        int count = 0;
        for (ServiceInstance instance : syncedInstances.values()) {
            if (nacosClient.deregisterInstance(instance)) {
                count++;
            }
        }
        syncedInstances.clear();
        log.info("Deregistered {} instances from Nacos", count);
        return count;
    }

    public int deregisterAllFromEureka() {
        int count = 0;
        for (ServiceInstance instance : syncedInstances.values()) {
            if (eurekaClient.deregisterInstance(instance.getServiceId(), instance.getInstanceId())) {
                count++;
            }
        }
        syncedInstances.clear();
        log.info("Deregistered {} instances from Eureka", count);
        return count;
    }

    public boolean deregisterFromNacos(ServiceInstance instance) {
        boolean result = nacosClient.deregisterInstance(instance);
        if (result) {
            syncedInstances.remove(instance.getInstanceId());
            log.info("Deregistered from Nacos: {}", instance.getInstanceId());
        }
        return result;
    }

    public boolean deregisterFromEureka(ServiceInstance instance) {
        boolean result = eurekaClient.deregisterInstance(instance.getServiceId(), instance.getInstanceId());
        if (result) {
            syncedInstances.remove(instance.getInstanceId());
            log.info("Deregistered from Eureka: {}", instance.getInstanceId());
        }
        return result;
    }

    public void shutdown() {
        stopAutoSync();
        syncExecutor.shutdown();
        try {
            if (!syncExecutor.awaitTermination(10, TimeUnit.SECONDS)) {
                syncExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            syncExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    private SyncResult syncFromSourceToTarget(SourceInstanceProvider sourceProvider,
                                               TargetRegister registerFunc,
                                               InstanceChecker checkFunc) throws Exception {
        SyncResult result = new SyncResult();
        List<ServiceInstance> sourceInstances = sourceProvider.getInstances();

        for (ServiceInstance instance : sourceInstances) {
            try {
                boolean exists = checkFunc.exists(instance);
                if (exists) {
                    result.skipped++;
                } else {
                    boolean registered = registerFunc.register(instance);
                    if (registered) {
                        result.synced++;
                    } else {
                        result.failed++;
                        result.failedInstances.add(instance.getInstanceId());
                    }
                }
            } catch (Exception e) {
                log.error("Failed to sync instance {}", instance.getInstanceId(), e);
                result.failed++;
                result.failedInstances.add(instance.getInstanceId());
            }
        }
        return result;
    }

    private Map<String, List<ServiceInstance>> buildInstanceMap(List<ServiceInstance> instances) {
        return instances.stream()
                .collect(Collectors.groupingBy(ServiceInstance::getServiceId));
    }

    private static class SyncResult {
        int synced = 0;
        int skipped = 0;
        int failed = 0;
        List<String> failedInstances = new ArrayList<>();
    }

    @FunctionalInterface
    private interface SourceInstanceProvider {
        List<ServiceInstance> getInstances() throws Exception;
    }

    @FunctionalInterface
    private interface TargetRegister {
        boolean register(ServiceInstance instance) throws Exception;
    }

    @FunctionalInterface
    private interface InstanceChecker {
        boolean exists(ServiceInstance instance) throws Exception;
    }
}

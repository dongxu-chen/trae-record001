package com.migration.rollback;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.engine.DualDiscoveryEngine;
import com.migration.engine.RegistrySyncEngine;
import com.migration.model.RollbackRecord;
import com.migration.model.RollbackRecord.RollbackStatus;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
public class RollbackManager {

    private final NacosClient nacosClient;
    private final EurekaClient eurekaClient;
    private final RegistrySyncEngine registrySyncEngine;
    private final DualDiscoveryEngine dualDiscoEngine;

    private final Map<String, RollbackRecord> rollbackRecords = new ConcurrentHashMap<>();
    private final List<RollbackRecord> rollbackHistory = Collections.synchronizedList(new ArrayList<>());

    public RollbackManager(NacosClient nacosClient,
                            EurekaClient eurekaClient,
                            RegistrySyncEngine registrySyncEngine,
                            DualDiscoveryEngine dualDiscoveryEngine) {
        this.nacosClient = nacosClient;
        this.eurekaClient = eurekaClient;
        this.registrySyncEngine = registrySyncEngine;
        this.dualDiscoEngine = dualDiscoveryEngine;
    }

    public void executeRollback(String taskId,
                                 Map<String, List<ServiceInstance>> originalSnapshot,
                                 String reason) {
        log.warn("Starting rollback for task {}: {}", taskId, reason);

        if (originalSnapshot == null || originalSnapshot.isEmpty()) {
            log.error("No snapshot available for rollback of task {}", taskId);
            return;
        }

        int totalServices = originalSnapshot.values().stream().mapToInt(List::size).sum();
        int rolledBack = 0;

        for (Map.Entry<String, List<ServiceInstance>> entry : originalSnapshot.entrySet()) {
            String serviceId = entry.getKey();
            List<ServiceInstance> originalInstances = entry.getValue();

            for (ServiceInstance instance : originalInstances) {
                String rollbackId = UUID.randomUUID().toString();
                RollbackRecord record = RollbackRecord.builder()
                        .rollbackId(rollbackId)
                        .taskId(taskId)
                        .serviceId(serviceId)
                        .status(RollbackStatus.IN_PROGRESS)
                        .reason(reason)
                        .rollbackTime(System.currentTimeMillis())
                        .build();
                rollbackRecords.put(rollbackId, record);

                try {
                    boolean nacosDereg = nacosClient.deregisterInstance(instance);
                    record.setNacosDeregistered(nacosDereg);
                    log.info("Rollback: deregistered {} from Nacos: {}", instance.getInstanceId(), nacosDereg);

                    List<ServiceInstance> currentEurekaInstances = eurekaClient.getInstances(serviceId);
                    boolean eurekaHasInstance = currentEurekaInstances.stream()
                            .anyMatch(i -> i.getHost().equals(instance.getHost()) && i.getPort() == instance.getPort());

                    if (!eurekaHasInstance) {
                        boolean eurekaReg = eurekaClient.registerInstance(instance);
                        record.setEurekaRestored(eurekaReg);
                        log.info("Rollback: re-registered {} in Eureka: {}", instance.getInstanceId(), eurekaReg);
                    } else {
                        record.setEurekaRestored(true);
                        log.info("Rollback: {} still exists in Eureka, no need to re-register", instance.getInstanceId());
                    }

                    record.setStatus(nacosDereg && record.isEurekaRestored()
                            ? RollbackStatus.SUCCESS : RollbackStatus.FAILED);
                    rolledBack++;

                } catch (Exception e) {
                    log.error("Rollback failed for instance {}", instance.getInstanceId(), e);
                    record.setStatus(RollbackStatus.FAILED);
                }

                rollbackHistory.add(record);
            }
        }

        dualDiscoEngine.setMode(DualDiscoveryEngine.DiscoveryMode.EUREKA_ONLY);
        registrySyncEngine.stopAutoSync();
        registrySyncEngine.deregisterAllFromNacos();

        log.warn("Rollback completed for task {}: {}/{} instances rolled back", taskId, rolledBack, totalServices);
    }

    public RollbackRecord rollbackSingleService(String serviceId, String reason) {
        String rollbackId = UUID.randomUUID().toString();
        RollbackRecord record = RollbackRecord.builder()
                .rollbackId(rollbackId)
                .serviceId(serviceId)
                .status(RollbackStatus.IN_PROGRESS)
                .reason(reason)
                .rollbackTime(System.currentTimeMillis())
                .build();
        rollbackRecords.put(rollbackId, record);

        try {
            List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);
            for (ServiceInstance instance : nacosInstances) {
                boolean nacosDereg = nacosClient.deregisterInstance(instance);
                record.setNacosDeregistered(nacosDereg);
            }

            dualDiscoEngine.setServiceTrafficRatio(serviceId, 0.0);

            List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
            if (eurekaInstances.isEmpty()) {
                log.warn("No instances in Eureka for service {} during rollback", serviceId);
            }

            record.setEurekaRestored(true);
            record.setStatus(RollbackStatus.SUCCESS);
            log.info("Single service rollback completed for {}", serviceId);

        } catch (Exception e) {
            log.error("Single service rollback failed for {}", serviceId, e);
            record.setStatus(RollbackStatus.FAILED);
        }

        rollbackHistory.add(record);
        return record;
    }

    public List<RollbackRecord> getRollbackHistory() {
        return Collections.unmodifiableList(rollbackHistory);
    }

    public List<RollbackRecord> getRollbackHistoryForTask(String taskId) {
        return rollbackHistory.stream()
                .filter(r -> taskId.equals(r.getTaskId()))
                .collect(Collectors.toList());
    }

    public Map<String, Object> generateRollbackPlan(Map<String, List<ServiceInstance>> snapshot) {
        Map<String, Object> plan = new LinkedHashMap<>();
        plan.put("generatedAt", System.currentTimeMillis());
        plan.put("totalServices", snapshot.size());
        plan.put("totalInstances", snapshot.values().stream().mapToInt(List::size).sum());

        List<Map<String, Object>> steps = new ArrayList<>();

        steps.add(Map.of("step", 1, "action", "STOP_MIGRATION",
                "description", "Stop all migration tasks and heartbeat threads"));

        steps.add(Map.of("step", 2, "action", "SWITCH_TO_EUREKA",
                "description", "Switch discovery mode to Eureka only"));

        steps.add(Map.of("step", 3, "action", "DEREGISTER_FROM_NACOS",
                "description", "Deregister all instances from Nacos",
                "instanceCount", snapshot.values().stream().mapToInt(List::size).sum()));

        steps.add(Map.of("step", 4, "action", "VERIFY_EUREKA",
                "description", "Verify all services are still registered in Eureka"));

        steps.add(Map.of("step", 5, "action", "RESTORE_MISSING",
                "description", "Re-register any missing instances in Eureka from snapshot"));

        steps.add(Map.of("step", 6, "action", "VALIDATE",
                "description", "Validate service discovery is working correctly"));

        plan.put("steps", steps);
        plan.put("estimatedTimeSeconds", snapshot.size() * 2);
        plan.put("riskLevel", snapshot.size() > 100 ? "HIGH" : snapshot.size() > 20 ? "MEDIUM" : "LOW");

        return plan;
    }
}

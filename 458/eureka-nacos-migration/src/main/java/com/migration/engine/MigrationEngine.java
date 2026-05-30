package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.config.MigrationProperties;
import com.migration.model.*;
import com.migration.monitor.MigrationMonitor;
import com.migration.rollback.RollbackManager;
import com.migration.verify.ConsistencyVerifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class MigrationEngine {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final RegistrySyncEngine registrySyncEngine;
    private final DualDiscoveryEngine dualDiscoEngine;
    private final ConsistencyVerifier consistencyVerifier;
    private final MigrationMonitor monitor;
    private final RollbackManager rollbackManager;
    private final MigrationProperties properties;

    private final Map<String, MigrationTask> tasks = new ConcurrentHashMap<>();
    private final Map<String, Map<String, List<ServiceInstance>>> eurekaSnapshots = new ConcurrentHashMap<>();

    public MigrationEngine(EurekaClient eurekaClient,
                            NacosClient nacosClient,
                            RegistrySyncEngine registrySyncEngine,
                            DualDiscoveryEngine dualDiscoEngine,
                            ConsistencyVerifier consistencyVerifier,
                            MigrationMonitor monitor,
                            RollbackManager rollbackManager,
                            MigrationProperties properties) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
        this.registrySyncEngine = registrySyncEngine;
        this.dualDiscoEngine = dualDiscoEngine;
        this.consistencyVerifier = consistencyVerifier;
        this.monitor = monitor;
        this.rollbackManager = rollbackManager;
        this.properties = properties;
    }

    public MigrationTask startFullMigration() {
        String taskId = UUID.randomUUID().toString();
        MigrationTask task = MigrationTask.builder()
                .taskId(taskId)
                .phase(MigrationTask.TaskPhase.SNAPSHOT)
                .status(MigrationTask.TaskStatus.RUNNING)
                .startTime(System.currentTimeMillis())
                .progress(0)
                .message("Migration started")
                .build();
        tasks.put(taskId, task);
        monitor.registerTask(task);

        new Thread(() -> executeMigration(taskId), "migration-" + taskId.substring(0, 8)).start();
        return task;
    }

    public MigrationTask startServiceMigration(String serviceId) {
        String taskId = UUID.randomUUID().toString();
        MigrationTask task = MigrationTask.builder()
                .taskId(taskId)
                .serviceId(serviceId)
                .phase(MigrationTask.TaskPhase.SNAPSHOT)
                .status(MigrationTask.TaskStatus.RUNNING)
                .startTime(System.currentTimeMillis())
                .progress(0)
                .message("Service migration started: " + serviceId)
                .build();
        tasks.put(taskId, task);
        monitor.registerTask(task);

        new Thread(() -> executeSingleServiceMigration(taskId, serviceId), "migration-" + taskId.substring(0, 8)).start();
        return task;
    }

    private void executeMigration(String taskId) {
        MigrationTask task = tasks.get(taskId);
        try {
            log.info("[{}] Phase 1: Taking Eureka snapshot", taskId);
            updatePhase(task, MigrationTask.TaskPhase.SNAPSHOT, 5);
            Map<String, List<ServiceInstance>> snapshot = dualDiscoEngine.getEurekaSnapshot();
            eurekaSnapshots.put(taskId, snapshot);
            monitor.updateSnapshot(taskId, snapshot);
            log.info("[{}] Snapshot taken: {} services", taskId, snapshot.size());

            log.info("[{}] Phase 2: Registry sync - Eureka to Nacos", taskId);
            updatePhase(task, MigrationTask.TaskPhase.DUAL_REGISTER, 10);
            registrySyncEngine.setSyncDirection(RegistrySyncEngine.SyncDirection.EUREKA_TO_NACOS);
            RegistrySyncEngine.SyncRecord syncRecord = registrySyncEngine.syncOnce();

            int totalInstances = syncRecord.getSyncedCount() + syncRecord.getSkippedCount() + syncRecord.getFailedCount();
            int registered = syncRecord.getSyncedCount() + syncRecord.getSkippedCount();
            int progress = 10 + (int) ((registered / (double) Math.max(totalInstances, 1)) * 30);
            updatePhase(task, MigrationTask.TaskPhase.DUAL_REGISTER, progress);

            log.info("[{}] Registry sync completed: synced={}, skipped={}, failed={}",
                    taskId, syncRecord.getSyncedCount(), syncRecord.getSkippedCount(), syncRecord.getFailedCount());

            log.info("[{}] Phase 3: Starting auto registry sync", taskId);
            updatePhase(task, MigrationTask.TaskPhase.DUAL_DISCOVER, 45);
            dualDiscoEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_PREFER_EUREKA);
            registrySyncEngine.startAutoSync();

            log.info("[{}] Phase 4: Verifying consistency", taskId);
            updatePhase(task, MigrationTask.TaskPhase.VERIFY_CONSISTENCY, 55);
            ConsistencyCheckResult checkResult = consistencyVerifier.verify(snapshot);
            monitor.recordConsistencyCheck(taskId, checkResult);

            if (!checkResult.isConsistent()) {
                log.warn("[{}] Consistency check found differences: {} mismatches, {} alerts",
                        taskId, checkResult.getMismatchedServices(),
                        checkResult.getAlerts() != null ? checkResult.getAlerts().size() : 0);
                if (properties.isAutoRollbackOnFailure() && checkResult.getMismatchedServices() > totalInstances / 2) {
                    log.error("[{}] Too many mismatches, triggering auto-rollback", taskId);
                    triggerRollback(taskId, "Consistency check failed: too many mismatches");
                    return;
                }
            }

            log.info("[{}] Phase 5: Grayscale traffic switching - {}% to Nacos",
                    taskId, (int) (properties.getGrayscaleRatio() * 100));
            updatePhase(task, MigrationTask.TaskPhase.GRAYSCALE_SWITCH, 65);
            dualDiscoEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_BALANCED);
            for (String serviceId : snapshot.keySet()) {
                dualDiscoEngine.setServiceTrafficRatio(serviceId, properties.getGrayscaleRatio());
            }

            log.info("[{}] Waiting for grayscale validation...", taskId);
            Thread.sleep(10000);

            ConsistencyCheckResult grayscaleCheck = consistencyVerifier.verify(snapshot);
            monitor.recordConsistencyCheck(taskId, grayscaleCheck);

            if (!grayscaleCheck.isConsistent() && grayscaleCheck.getAlerts() != null) {
                log.warn("[{}] Grayscale phase alerts: {} issues detected",
                        taskId, grayscaleCheck.getAlerts().size());
                for (String alert : grayscaleCheck.getAlerts()) {
                    log.warn("[{}] {}", taskId, alert);
                }
            }

            log.info("[{}] Phase 6: Full traffic switch to Nacos", taskId);
            updatePhase(task, MigrationTask.TaskPhase.FULL_SWITCH, 85);
            dualDiscoEngine.setMode(DualDiscoveryEngine.DiscoveryMode.NACOS_ONLY);
            for (String serviceId : snapshot.keySet()) {
                dualDiscoEngine.setServiceTrafficRatio(serviceId, 1.0);
            }

            log.info("[{}] Phase 7: Deregistering from Eureka", taskId);
            updatePhase(task, MigrationTask.TaskPhase.DEREGISTER_EUREKA, 95);
            registrySyncEngine.stopAutoSync();
            registrySyncEngine.deregisterAllFromEureka();

            updatePhase(task, MigrationTask.TaskPhase.COMPLETED, 100);
            task.setStatus(MigrationTask.TaskStatus.SUCCESS);
            task.setEndTime(System.currentTimeMillis());
            task.setMessage("Migration completed successfully. " +
                    "Synced: " + syncRecord.getSyncedCount() +
                    ", Skipped: " + syncRecord.getSkippedCount() +
                    ", Failed: " + syncRecord.getFailedCount());
            log.info("[{}] Migration completed successfully", taskId);

        } catch (Exception e) {
            log.error("[{}] Migration failed", taskId, e);
            task.setStatus(MigrationTask.TaskStatus.FAILED);
            task.setMessage("Migration failed: " + e.getMessage());
            task.setEndTime(System.currentTimeMillis());

            if (properties.isAutoRollbackOnFailure()) {
                triggerRollback(taskId, "Migration failed: " + e.getMessage());
            }
        }
    }

    private void executeSingleServiceMigration(String taskId, String serviceId) {
        MigrationTask task = tasks.get(taskId);
        try {
            log.info("[{}] Migrating service: {}", taskId, serviceId);

            updatePhase(task, MigrationTask.TaskPhase.SNAPSHOT, 10);
            List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
            Map<String, List<ServiceInstance>> snapshot = Map.of(serviceId, eurekaInstances);
            eurekaSnapshots.put(taskId, snapshot);

            updatePhase(task, MigrationTask.TaskPhase.DUAL_REGISTER, 25);
            registrySyncEngine.setSyncDirection(RegistrySyncEngine.SyncDirection.EUREKA_TO_NACOS);
            RegistrySyncEngine.SyncRecord syncRecord = registrySyncEngine.syncOnce();

            updatePhase(task, MigrationTask.TaskPhase.DUAL_DISCOVER, 40);
            dualDiscoEngine.setMode(DualDiscoveryEngine.DiscoveryMode.DUAL_PREFER_EUREKA);

            updatePhase(task, MigrationTask.TaskPhase.VERIFY_CONSISTENCY, 55);
            ConsistencyCheckResult checkResult = consistencyVerifier.verify(snapshot);
            monitor.recordConsistencyCheck(taskId, checkResult);

            if (checkResult.getAlerts() != null && !checkResult.getAlerts().isEmpty()) {
                log.warn("[{}] Consistency check alerts for service {}:", taskId, serviceId);
                for (String alert : checkResult.getAlerts()) {
                    log.warn("[{}] {}", taskId, alert);
                }
            }

            updatePhase(task, MigrationTask.TaskPhase.GRAYSCALE_SWITCH, 70);
            dualDiscoEngine.setServiceTrafficRatio(serviceId, properties.getGrayscaleRatio());

            Thread.sleep(5000);

            updatePhase(task, MigrationTask.TaskPhase.FULL_SWITCH, 85);
            dualDiscoEngine.setServiceTrafficRatio(serviceId, 1.0);

            updatePhase(task, MigrationTask.TaskPhase.DEREGISTER_EUREKA, 95);
            for (ServiceInstance instance : eurekaInstances) {
                registrySyncEngine.deregisterFromEureka(instance);
            }

            updatePhase(task, MigrationTask.TaskPhase.COMPLETED, 100);
            task.setStatus(MigrationTask.TaskStatus.SUCCESS);
            task.setEndTime(System.currentTimeMillis());
            task.setMessage("Service migration completed: " + serviceId +
                    ", Synced: " + syncRecord.getSyncedCount());
            log.info("[{}] Service {} migrated successfully", taskId, serviceId);

        } catch (Exception e) {
            log.error("[{}] Service migration failed for {}", taskId, serviceId, e);
            task.setStatus(MigrationTask.TaskStatus.FAILED);
            task.setMessage("Service migration failed: " + e.getMessage());
            task.setEndTime(System.currentTimeMillis());
        }
    }

    public void triggerRollback(String taskId, String reason) {
        MigrationTask task = tasks.get(taskId);
        if (task == null) return;

        log.warn("[{}] Triggering rollback: {}", taskId, reason);
        task.setStatus(MigrationTask.TaskStatus.ROLLBACK);
        task.setMessage("Rollback in progress: " + reason);

        registrySyncEngine.stopAutoSync();

        Map<String, List<ServiceInstance>> snapshot = eurekaSnapshots.get(taskId);
        rollbackManager.executeRollback(taskId, snapshot, reason);

        task.setStatus(MigrationTask.TaskStatus.ROLLBACK);
        task.setMessage("Rollback completed: " + reason);
        task.setEndTime(System.currentTimeMillis());
    }

    private void updatePhase(MigrationTask task, MigrationTask.TaskPhase phase, int progress) {
        task.setPhase(phase);
        task.setProgress(progress);
        monitor.updateProgress(task.getTaskId(), phase, progress);
    }

    public MigrationTask getTask(String taskId) {
        return tasks.get(taskId);
    }

    public Collection<MigrationTask> getAllTasks() {
        return tasks.values();
    }

    public Map<String, List<ServiceInstance>> getSnapshot(String taskId) {
        return eurekaSnapshots.get(taskId);
    }

    public RegistrySyncEngine getRegistrySyncEngine() {
        return registrySyncEngine;
    }
}

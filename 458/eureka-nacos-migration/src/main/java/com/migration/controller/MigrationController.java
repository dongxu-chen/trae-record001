package com.migration.controller;

import com.migration.engine.DualDiscoveryEngine;
import com.migration.engine.MigrationEngine;
import com.migration.engine.RegistrySyncEngine;
import com.migration.engine.RegistrySyncEngine.SyncRecord;
import com.migration.engine.RegistrySyncEngine.SyncDirection;
import com.migration.model.*;
import com.migration.monitor.MigrationMonitor;
import com.migration.traffic.TrafficRouter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/migration")
public class MigrationController {

    private final MigrationEngine migrationEngine;
    private final RegistrySyncEngine registrySyncEngine;
    private final DualDiscoveryEngine dualDiscoEngine;
    private final MigrationMonitor monitor;
    private final TrafficRouter trafficRouter;

    public MigrationController(MigrationEngine migrationEngine,
                                RegistrySyncEngine registrySyncEngine,
                                DualDiscoveryEngine dualDiscoEngine,
                                MigrationMonitor monitor,
                                TrafficRouter trafficRouter) {
        this.migrationEngine = migrationEngine;
        this.registrySyncEngine = registrySyncEngine;
        this.dualDiscoEngine = dualDiscoEngine;
        this.monitor = monitor;
        this.trafficRouter = trafficRouter;
    }

    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> startFullMigration() {
        MigrationTask task = migrationEngine.startFullMigration();
        return ResponseEntity.ok(taskToMap(task));
    }

    @PostMapping("/service/{serviceId}")
    public ResponseEntity<Map<String, Object>> startServiceMigration(@PathVariable String serviceId) {
        MigrationTask task = migrationEngine.startServiceMigration(serviceId);
        return ResponseEntity.ok(taskToMap(task));
    }

    @PostMapping("/sync")
    public ResponseEntity<Map<String, Object>> syncOnce(@RequestParam(required = false) String direction) {
        SyncDirection syncDirection = direction != null
                ? SyncDirection.valueOf(direction.toUpperCase())
                : registrySyncEngine.getSyncDirection();

        SyncRecord record = registrySyncEngine.syncOnce(syncDirection);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("syncId", record.getSyncId());
        result.put("direction", record.getDirection());
        result.put("syncedCount", record.getSyncedCount());
        result.put("skippedCount", record.getSkippedCount());
        result.put("failedCount", record.getFailedCount());
        result.put("failedInstances", record.getFailedInstances());
        result.put("timestamp", record.getTimestamp());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/sync/auto/start")
    public ResponseEntity<Map<String, Object>> startAutoSync(@RequestParam(required = false) String direction) {
        if (direction != null) {
            registrySyncEngine.setSyncDirection(SyncDirection.valueOf(direction.toUpperCase()));
        }
        registrySyncEngine.startAutoSync();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("message", "Auto registry sync started");
        result.put("direction", registrySyncEngine.getSyncDirection());
        result.put("syncedInstanceCount", registrySyncEngine.getSyncedInstances().size());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/sync/auto/stop")
    public ResponseEntity<Map<String, Object>> stopAutoSync() {
        registrySyncEngine.stopAutoSync();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("message", "Auto registry sync stopped");
        result.put("syncedInstanceCount", registrySyncEngine.getSyncedInstances().size());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/sync/status")
    public ResponseEntity<Map<String, Object>> getSyncStatus() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("syncRunning", registrySyncEngine.isSyncRunning());
        result.put("syncMode", registrySyncEngine.getSyncMode());
        result.put("syncDirection", registrySyncEngine.getSyncDirection());
        result.put("syncedInstanceCount", registrySyncEngine.getSyncedInstances().size());
        result.put("syncHistorySize", registrySyncEngine.getSyncHistory().size());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/sync/history")
    public ResponseEntity<List<SyncRecord>> getSyncHistory() {
        return ResponseEntity.ok(registrySyncEngine.getSyncHistory());
    }

    @GetMapping("/sync/instances")
    public ResponseEntity<Map<String, List<ServiceInstance>>> getConsolidatedInstances() {
        return ResponseEntity.ok(registrySyncEngine.getConsolidatedInstanceList());
    }

    @PutMapping("/sync/direction/{direction}")
    public ResponseEntity<Map<String, Object>> setSyncDirection(@PathVariable String direction) {
        try {
            SyncDirection syncDirection = SyncDirection.valueOf(direction.toUpperCase());
            registrySyncEngine.setSyncDirection(syncDirection);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("direction", syncDirection);
            result.put("message", "Sync direction updated");
            return ResponseEntity.ok(result);
        } catch (IllegalArgumentException e) {
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("error", "Invalid direction. Valid directions: EUREKA_TO_NACOS, NACOS_TO_EUREKA, BIDIRECTIONAL");
            return ResponseEntity.badRequest().body(error);
        }
    }

    @PostMapping("/deregister/nacos")
    public ResponseEntity<Map<String, Object>> deregisterFromNacos(@RequestBody ServiceInstance instance) {
        boolean success = registrySyncEngine.deregisterFromNacos(instance);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", success);
        result.put("instanceId", instance.getInstanceId());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/deregister/eureka")
    public ResponseEntity<Map<String, Object>> deregisterFromEureka(@RequestBody ServiceInstance instance) {
        boolean success = registrySyncEngine.deregisterFromEureka(instance);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", success);
        result.put("instanceId", instance.getInstanceId());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/traffic/ratio")
    public ResponseEntity<Map<String, Object>> setTrafficRatio(@RequestParam String serviceId,
                                                                @RequestParam double nacosRatio) {
        GrayscaleStrategy strategy = trafficRouter.setTrafficRatio(serviceId, nacosRatio);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceId", serviceId);
        result.put("nacosRatio", strategy.getNacosTrafficRatio());
        result.put("nacosPercentage", strategy.getNacosPercentage());
        result.put("eurekaPercentage", 100 - strategy.getNacosPercentage());
        result.put("status", strategy.getStatusDescription());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/traffic/percentage")
    public ResponseEntity<Map<String, Object>> setTrafficPercentage(@RequestParam String serviceId,
                                                                    @RequestParam int nacosPercentage) {
        GrayscaleStrategy strategy = trafficRouter.setTrafficPercentage(serviceId, nacosPercentage);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceId", serviceId);
        result.put("nacosRatio", strategy.getNacosTrafficRatio());
        result.put("nacosPercentage", strategy.getNacosPercentage());
        result.put("eurekaPercentage", 100 - strategy.getNacosPercentage());
        result.put("status", strategy.getStatusDescription());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/traffic/global/ratio")
    public ResponseEntity<Map<String, Object>> setGlobalTrafficRatio(@RequestParam double nacosRatio) {
        trafficRouter.setGlobalTrafficRatio(nacosRatio);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("nacosRatio", nacosRatio);
        result.put("nacosPercentage", (int) (nacosRatio * 100));
        result.put("message", "Global traffic ratio updated");
        return ResponseEntity.ok(result);
    }

    @PostMapping("/traffic/global/percentage")
    public ResponseEntity<Map<String, Object>> setGlobalTrafficPercentage(@RequestParam int nacosPercentage) {
        trafficRouter.setGlobalTrafficPercentage(nacosPercentage);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("nacosPercentage", nacosPercentage);
        result.put("message", "Global traffic percentage updated");
        return ResponseEntity.ok(result);
    }

    @GetMapping("/traffic/status")
    public ResponseEntity<Map<String, Map<String, Object>>> getAllTrafficStatus() {
        return ResponseEntity.ok(trafficRouter.getAllTrafficStatus());
    }

    @GetMapping("/traffic/status/{serviceId}")
    public ResponseEntity<Map<String, Object>> getTrafficStatus(@PathVariable String serviceId) {
        return ResponseEntity.ok(trafficRouter.getTrafficStatus(serviceId));
    }

    @GetMapping("/discovery/mode")
    public ResponseEntity<Map<String, Object>> getDiscoveryMode() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mode", dualDiscoEngine.getMode());
        return ResponseEntity.ok(result);
    }

    @PutMapping("/discovery/mode/{mode}")
    public ResponseEntity<Map<String, Object>> setDiscoveryMode(@PathVariable String mode) {
        try {
            DualDiscoveryEngine.DiscoveryMode discoveryMode = DualDiscoveryEngine.DiscoveryMode.valueOf(mode.toUpperCase());
            dualDiscoEngine.setMode(discoveryMode);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("mode", discoveryMode);
            result.put("message", "Discovery mode updated");
            return ResponseEntity.ok(result);
        } catch (IllegalArgumentException e) {
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("error", "Invalid mode. Valid modes: EUREKA_ONLY, NACOS_ONLY, DUAL_PREFER_EUREKA, DUAL_PREFER_NACOS, DUAL_BALANCED");
            return ResponseEntity.badRequest().body(error);
        }
    }

    @GetMapping("/task/{taskId}")
    public ResponseEntity<Map<String, Object>> getTask(@PathVariable String taskId) {
        MigrationTask task = migrationEngine.getTask(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(taskToMap(task));
    }

    @GetMapping("/tasks")
    public ResponseEntity<Object> getAllTasks() {
        return ResponseEntity.ok(migrationEngine.getAllTasks());
    }

    @GetMapping("/snapshot/{taskId}")
    public ResponseEntity<Object> getSnapshot(@PathVariable String taskId) {
        Map<String, List<ServiceInstance>> snapshot = migrationEngine.getSnapshot(taskId);
        if (snapshot == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(snapshot);
    }

    private Map<String, Object> taskToMap(MigrationTask task) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("taskId", task.getTaskId());
        map.put("serviceId", task.getServiceId());
        map.put("phase", task.getPhase());
        map.put("status", task.getStatus());
        map.put("progress", task.getProgress());
        map.put("message", task.getMessage());
        map.put("startTime", task.getStartTime());
        map.put("endTime", task.getEndTime());
        return map;
    }
}

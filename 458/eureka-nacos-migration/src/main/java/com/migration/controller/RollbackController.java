package com.migration.controller;

import com.migration.engine.MigrationEngine;
import com.migration.model.ConsistencyCheckResult;
import com.migration.model.ConsistencyCheckResult.MetadataDiff;
import com.migration.model.PerformanceMetrics;
import com.migration.model.RollbackRecord;
import com.migration.model.ServiceInstance;
import com.migration.report.PerformanceReporter;
import com.migration.rollback.RollbackManager;
import com.migration.traffic.GrayscaleStrategy;
import com.migration.traffic.TrafficRouter;
import com.migration.verify.ConsistencyVerifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api")
public class RollbackController {

    private final RollbackManager rollbackManager;
    private final MigrationEngine migrationEngine;
    private final ConsistencyVerifier consistencyVerifier;
    private final TrafficRouter trafficRouter;
    private final PerformanceReporter performanceReporter;

    public RollbackController(RollbackManager rollbackManager,
                               MigrationEngine migrationEngine,
                               ConsistencyVerifier consistencyVerifier,
                               TrafficRouter trafficRouter,
                               PerformanceReporter performanceReporter) {
        this.rollbackManager = rollbackManager;
        this.migrationEngine = migrationEngine;
        this.consistencyVerifier = consistencyVerifier;
        this.trafficRouter = trafficRouter;
        this.performanceReporter = performanceReporter;
    }

    @PostMapping("/rollback/task/{taskId}")
    public ResponseEntity<Map<String, Object>> rollbackTask(@PathVariable String taskId,
                                                             @RequestParam(required = false, defaultValue = "Manual rollback") String reason) {
        migrationEngine.triggerRollback(taskId, reason);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("taskId", taskId);
        result.put("status", "ROLLBACK_INITIATED");
        result.put("reason", reason);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/rollback/service/{serviceId}")
    public ResponseEntity<Map<String, Object>> rollbackService(@PathVariable String serviceId,
                                                                @RequestParam(required = false, defaultValue = "Manual rollback") String reason) {
        RollbackRecord record = rollbackManager.rollbackSingleService(serviceId, reason);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("rollbackId", record.getRollbackId());
        result.put("serviceId", serviceId);
        result.put("status", record.getStatus());
        result.put("nacosDeregistered", record.isNacosDeregistered());
        result.put("eurekaRestored", record.isEurekaRestored());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/rollback/history")
    public ResponseEntity<List<RollbackRecord>> getRollbackHistory() {
        return ResponseEntity.ok(rollbackManager.getRollbackHistory());
    }

    @GetMapping("/rollback/history/{taskId}")
    public ResponseEntity<List<RollbackRecord>> getRollbackHistoryForTask(@PathVariable String taskId) {
        return ResponseEntity.ok(rollbackManager.getRollbackHistoryForTask(taskId));
    }

    @GetMapping("/rollback/plan")
    public ResponseEntity<Map<String, Object>> generateRollbackPlan() {
        Map<String, List<ServiceInstance>> snapshot = new LinkedHashMap<>();
        if (!migrationEngine.getAllTasks().isEmpty()) {
            String firstTaskId = migrationEngine.getAllTasks().iterator().next().getTaskId();
            snapshot = migrationEngine.getSnapshot(firstTaskId);
        }
        if (snapshot == null) {
            snapshot = Map.of();
        }
        return ResponseEntity.ok(rollbackManager.generateRollbackPlan(snapshot));
    }

    @PostMapping("/consistency/verify")
    public ResponseEntity<Map<String, Object>> runConsistencyCheck() {
        ConsistencyCheckResult result = consistencyVerifier.quickVerify();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("checkId", result.getCheckId());
        response.put("consistent", result.isConsistent());
        response.put("totalServices", result.getTotalServices());
        response.put("matchedServices", result.getMatchedServices());
        response.put("mismatchedServices", result.getMismatchedServices());
        response.put("onlyInEureka", result.getOnlyInEureka());
        response.put("onlyInNacos", result.getOnlyInNacos());
        response.put("differences", result.getDifferences());
        response.put("alerts", result.getAlerts());
        response.put("alertCount", result.getAlerts() != null ? result.getAlerts().size() : 0);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/consistency/verify/{taskId}")
    public ResponseEntity<Map<String, Object>> verifyTask(@PathVariable String taskId) {
        Map<String, List<ServiceInstance>> snapshot = migrationEngine.getSnapshot(taskId);
        if (snapshot == null) {
            return ResponseEntity.notFound().build();
        }
        ConsistencyCheckResult result = consistencyVerifier.verify(snapshot);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("checkId", result.getCheckId());
        response.put("consistent", result.isConsistent());
        response.put("totalServices", result.getTotalServices());
        response.put("matchedServices", result.getMatchedServices());
        response.put("mismatchedServices", result.getMismatchedServices());
        response.put("onlyInEureka", result.getOnlyInEureka());
        response.put("onlyInNacos", result.getOnlyInNacos());
        response.put("differences", result.getDifferences());
        response.put("alerts", result.getAlerts());
        response.put("alertCount", result.getAlerts() != null ? result.getAlerts().size() : 0);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/consistency/metadata/{serviceId}/{instanceKey}")
    public ResponseEntity<List<MetadataDiff>> compareInstanceMetadata(@PathVariable String serviceId,
                                                                       @PathVariable String instanceKey) {
        List<MetadataDiff> diffs = consistencyVerifier.compareInstanceMetadata(serviceId, instanceKey);
        return ResponseEntity.ok(diffs);
    }

    @GetMapping("/consistency/alerts")
    public ResponseEntity<Map<String, Object>> getLatestAlerts() {
        ConsistencyCheckResult result = consistencyVerifier.quickVerify();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("consistent", result.isConsistent());
        response.put("alertCount", result.getAlerts() != null ? result.getAlerts().size() : 0);
        response.put("alerts", result.getAlerts());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/traffic/switch/nacos/{serviceId}")
    public ResponseEntity<Map<String, Object>> fullSwitchNacos(@PathVariable String serviceId) {
        trafficRouter.fullSwitchToNacos(serviceId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceId", serviceId);
        result.put("status", "FULL_NACOS");
        result.put("nacosPercentage", 100);
        result.put("message", "Traffic fully switched to Nacos");
        return ResponseEntity.ok(result);
    }

    @PostMapping("/traffic/switch/eureka/{serviceId}")
    public ResponseEntity<Map<String, Object>> fullSwitchEureka(@PathVariable String serviceId) {
        trafficRouter.fullSwitchToEureka(serviceId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceId", serviceId);
        result.put("status", "FULL_EUREKA");
        result.put("nacosPercentage", 0);
        result.put("message", "Traffic fully switched back to Eureka");
        return ResponseEntity.ok(result);
    }

    @GetMapping("/traffic/strategies")
    public ResponseEntity<Map<String, GrayscaleStrategy>> getGrayscaleStrategies() {
        return ResponseEntity.ok(trafficRouter.getAllStrategies());
    }

    @GetMapping("/report/performance")
    public ResponseEntity<Map<String, Object>> getPerformanceReport() {
        return ResponseEntity.ok(performanceReporter.generateComparisonReport());
    }

    @PostMapping("/report/benchmark/{serviceId}")
    public ResponseEntity<Map<String, Object>> benchmarkService(@PathVariable String serviceId) {
        PerformanceMetrics metrics = performanceReporter.benchmarkService(serviceId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceId", metrics.getServiceId());
        result.put("eurekaRegistrationMs", metrics.getEurekaRegistrationTimeMs());
        result.put("nacosRegistrationMs", metrics.getNacosRegistrationTimeMs());
        result.put("eurekaDiscoveryMs", metrics.getEurekaDiscoveryTimeMs());
        result.put("nacosDiscoveryMs", metrics.getNacosDiscoveryTimeMs());
        result.put("eurekaP99Ms", metrics.getEurekaP99Latency());
        result.put("nacosP99Ms", metrics.getNacosP99Latency());
        result.put("eurekaThroughput", metrics.getEurekaThroughput());
        result.put("nacosThroughput", metrics.getNacosThroughput());
        return ResponseEntity.ok(result);
    }
}

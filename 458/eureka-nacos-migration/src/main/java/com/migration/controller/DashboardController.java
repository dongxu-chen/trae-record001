package com.migration.controller;

import com.migration.engine.MigrationPlanEngine;
import com.migration.engine.SwitchRehearsalEngine;
import com.migration.model.MigrationPlan;
import com.migration.model.MigrationPlan.PlanStrategy;
import com.migration.model.MonitoringDashboard;
import com.migration.model.SwitchRehearsal;
import com.migration.model.SwitchRehearsal.RehearsalType;
import com.migration.monitor.MonitoringDashboardService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final MonitoringDashboardService dashboardService;
    private final MigrationPlanEngine planEngine;
    private final SwitchRehearsalEngine rehearsalEngine;

    public DashboardController(MonitoringDashboardService dashboardService,
                               MigrationPlanEngine planEngine,
                               SwitchRehearsalEngine rehearsalEngine) {
        this.dashboardService = dashboardService;
        this.planEngine = planEngine;
        this.rehearsalEngine = rehearsalEngine;
    }

    @GetMapping
    public ResponseEntity<MonitoringDashboard> getDashboard() {
        return ResponseEntity.ok(dashboardService.generateDashboard());
    }

    @GetMapping("/overview")
    public ResponseEntity<Map<String, Object>> getOverview() {
        MonitoringDashboard dashboard = dashboardService.generateDashboard();
        Map<String, Object> overview = new LinkedHashMap<>();
        overview.put("generatedAt", dashboard.getGeneratedAt());
        overview.put("migrationOverview", dashboard.getMigrationOverview());
        overview.put("serviceHealth", dashboard.getServiceHealth());
        overview.put("registrySyncStatus", dashboard.getRegistrySyncStatus());
        overview.put("trafficDistribution", dashboard.getTrafficDistribution());
        return ResponseEntity.ok(overview);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getServiceHealth() {
        MonitoringDashboard dashboard = dashboardService.generateDashboard();
        Map<String, Object> health = new LinkedHashMap<>();
        health.put("eureka", Map.of(
                "totalServices", dashboard.getServiceHealth().getTotalServicesEureka(),
                "healthyServices", dashboard.getServiceHealth().getHealthyServicesEureka(),
                "unhealthyServices", dashboard.getServiceHealth().getUnhealthyServicesEureka(),
                "healthRate", dashboard.getServiceHealth().getEurekaHealthRate()
        ));
        health.put("nacos", Map.of(
                "totalServices", dashboard.getServiceHealth().getTotalServicesNacos(),
                "healthyServices", dashboard.getServiceHealth().getHealthyServicesNacos(),
                "unhealthyServices", dashboard.getServiceHealth().getUnhealthyServicesNacos(),
                "healthRate", dashboard.getServiceHealth().getNacosHealthRate()
        ));
        health.put("unhealthyServices", dashboard.getServiceHealth().getUnhealthyServices());
        return ResponseEntity.ok(health);
    }

    @GetMapping("/traffic")
    public ResponseEntity<Map<String, Object>> getTrafficDistribution() {
        MonitoringDashboard dashboard = dashboardService.generateDashboard();
        return ResponseEntity.ok(Map.of(
                "overallNacosRatio", dashboard.getTrafficDistribution().getOverallNacosRatio(),
                "overallEurekaRatio", dashboard.getTrafficDistribution().getOverallEurekaRatio(),
                "servicesFullNacos", dashboard.getTrafficDistribution().getServicesFullNacos(),
                "servicesFullEureka", dashboard.getTrafficDistribution().getServicesFullEureka(),
                "servicesGrayscale", dashboard.getTrafficDistribution().getServicesGrayscale(),
                "serviceDetails", dashboard.getTrafficDistribution().getServiceTrafficDetails()
        ));
    }

    @GetMapping("/alerts")
    public ResponseEntity<List<MonitoringDashboard.RecentAlert>> getRecentAlerts() {
        return ResponseEntity.ok(dashboardService.getRecentAlerts());
    }

    @PostMapping("/alerts/{alertId}/acknowledge")
    public ResponseEntity<Map<String, Object>> acknowledgeAlert(@PathVariable String alertId) {
        dashboardService.acknowledgeAlert(alertId);
        return ResponseEntity.ok(Map.of(
                "alertId", alertId,
                "acknowledged", true
        ));
    }

    @PostMapping("/alerts/refresh")
    public ResponseEntity<Map<String, Object>> refreshAlerts() {
        dashboardService.refreshAlertsFromConsistencyCheck();
        return ResponseEntity.ok(Map.of(
                "refreshed", true,
                "alertCount", dashboardService.getRecentAlerts().size()
        ));
    }

    @PostMapping("/plans")
    public ResponseEntity<Map<String, Object>> createPlan(@RequestBody Map<String, Object> request) {
        String planName = (String) request.getOrDefault("planName", "Migration Plan");
        String description = (String) request.getOrDefault("description", "");
        int batchSize = (int) request.getOrDefault("batchSize", 5);
        String strategyStr = (String) request.getOrDefault("strategy", "SEQUENTIAL");
        PlanStrategy strategy = PlanStrategy.valueOf(strategyStr.toUpperCase());

        MigrationPlan plan = planEngine.createPlan(planName, description, batchSize, strategy);

        if (request.containsKey("serviceIds")) {
            @SuppressWarnings("unchecked")
            List<String> serviceIds = (List<String>) request.get("serviceIds");
            planEngine.configureBatchServices(plan.getPlanId(), serviceIds, batchSize);
        } else {
            @SuppressWarnings("unchecked")
            List<String> priorityServices = (List<String>) request.get("priorityServices");
            @SuppressWarnings("unchecked")
            List<String> excludeServices = (List<String>) request.get("excludeServices");
            planEngine.autoConfigurePlan(plan.getPlanId(), batchSize, priorityServices, excludeServices);
        }

        return ResponseEntity.ok(planToMap(plan));
    }

    @GetMapping("/plans")
    public ResponseEntity<List<MigrationPlan>> getAllPlans() {
        return ResponseEntity.ok(planEngine.getAllPlans());
    }

    @GetMapping("/plans/{planId}")
    public ResponseEntity<MigrationPlan> getPlan(@PathVariable String planId) {
        MigrationPlan plan = planEngine.getPlan(planId);
        if (plan == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(plan);
    }

    @PostMapping("/plans/{planId}/start")
    public ResponseEntity<Map<String, Object>> startPlan(@PathVariable String planId) {
        try {
            MigrationPlan plan = planEngine.startPlan(planId);
            return ResponseEntity.ok(planToMap(plan));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", e.getMessage()
            ));
        }
    }

    @PostMapping("/plans/{planId}/pause")
    public ResponseEntity<Map<String, Object>> pausePlan(@PathVariable String planId) {
        MigrationPlan plan = planEngine.pausePlan(planId);
        return ResponseEntity.ok(planToMap(plan));
    }

    @PostMapping("/plans/{planId}/resume")
    public ResponseEntity<Map<String, Object>> resumePlan(@PathVariable String planId) {
        MigrationPlan plan = planEngine.resumePlan(planId);
        return ResponseEntity.ok(planToMap(plan));
    }

    @PostMapping("/plans/{planId}/cancel")
    public ResponseEntity<Map<String, Object>> cancelPlan(@PathVariable String planId) {
        MigrationPlan plan = planEngine.cancelPlan(planId);
        return ResponseEntity.ok(planToMap(plan));
    }

    @DeleteMapping("/plans/{planId}")
    public ResponseEntity<Map<String, Object>> deletePlan(@PathVariable String planId) {
        planEngine.deletePlan(planId);
        return ResponseEntity.ok(Map.of(
                "planId", planId,
                "deleted", true
        ));
    }

    @PostMapping("/rehearsals")
    public ResponseEntity<Map<String, Object>> createRehearsal(@RequestBody Map<String, Object> request) {
        String name = (String) request.getOrDefault("name", "Switch Rehearsal");
        String typeStr = (String) request.getOrDefault("type", "GRAYSCALE_PROGRESSION");
        RehearsalType type = RehearsalType.valueOf(typeStr.toUpperCase());
        @SuppressWarnings("unchecked")
        List<String> targetServices = (List<String>) request.getOrDefault("targetServices", List.of());
        int targetPercentage = (int) request.getOrDefault("targetPercentage", 100);

        SwitchRehearsal rehearsal = rehearsalEngine.createRehearsal(name, type, targetServices, targetPercentage);
        return ResponseEntity.ok(rehearsalToMap(rehearsal));
    }

    @PostMapping("/rehearsals/{rehearsalId}/execute")
    public ResponseEntity<Map<String, Object>> executeRehearsal(@PathVariable String rehearsalId) {
        try {
            SwitchRehearsal rehearsal = rehearsalEngine.executeRehearsal(rehearsalId);
            return ResponseEntity.ok(rehearsalToMap(rehearsal));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", e.getMessage()
            ));
        }
    }

    @GetMapping("/rehearsals")
    public ResponseEntity<List<SwitchRehearsal>> getAllRehearsals() {
        return ResponseEntity.ok(rehearsalEngine.getAllRehearsals());
    }

    @GetMapping("/rehearsals/{rehearsalId}")
    public ResponseEntity<SwitchRehearsal> getRehearsal(@PathVariable String rehearsalId) {
        SwitchRehearsal rehearsal = rehearsalEngine.getRehearsal(rehearsalId);
        if (rehearsal == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(rehearsal);
    }

    @DeleteMapping("/rehearsals/{rehearsalId}")
    public ResponseEntity<Map<String, Object>> deleteRehearsal(@PathVariable String rehearsalId) {
        rehearsalEngine.deleteRehearsal(rehearsalId);
        return ResponseEntity.ok(Map.of(
                "rehearsalId", rehearsalId,
                "deleted", true
        ));
    }

    private Map<String, Object> planToMap(MigrationPlan plan) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("planId", plan.getPlanId());
        map.put("planName", plan.getPlanName());
        map.put("description", plan.getDescription());
        map.put("status", plan.getStatus());
        map.put("strategy", plan.getStrategy());
        map.put("batchSize", plan.getBatchSize());
        map.put("totalBatches", plan.getTotalBatches());
        map.put("currentBatch", plan.getCurrentBatch());
        map.put("batches", plan.getBatches());
        map.put("createdAt", plan.getCreatedAt());
        map.put("startTime", plan.getStartTime());
        map.put("completedTime", plan.getCompletedTime());
        return map;
    }

    private Map<String, Object> rehearsalToMap(SwitchRehearsal rehearsal) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("rehearsalId", rehearsal.getRehearsalId());
        map.put("rehearsalName", rehearsal.getRehearsalName());
        map.put("type", rehearsal.getType());
        map.put("status", rehearsal.getStatus());
        map.put("targetServices", rehearsal.getTargetServices());
        map.put("targetTrafficPercentage", rehearsal.getTargetTrafficPercentage());
        map.put("steps", rehearsal.getSteps());
        map.put("result", rehearsal.getResult());
        map.put("createdAt", rehearsal.getCreatedAt());
        map.put("startTime", rehearsal.getStartTime());
        map.put("completedTime", rehearsal.getCompletedTime());
        return map;
    }
}

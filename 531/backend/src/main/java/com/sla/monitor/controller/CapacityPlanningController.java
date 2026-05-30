package com.sla.monitor.controller;

import com.sla.monitor.model.CapacityPlan;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.service.CapacityPlanningService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/capacity")
public class CapacityPlanningController {

    private final CapacityPlanningService capacityPlanningService;
    private final ServiceInfoRepository serviceInfoRepository;

    public CapacityPlanningController(CapacityPlanningService capacityPlanningService,
                                       ServiceInfoRepository serviceInfoRepository) {
        this.capacityPlanningService = capacityPlanningService;
        this.serviceInfoRepository = serviceInfoRepository;
    }

    @GetMapping
    public List<CapacityPlan> getAllCapacityPlans(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false, defaultValue = "7") int days) {
        if (serviceName != null) {
            return capacityPlanningService.getCapacityPlansForService(serviceName);
        }
        return capacityPlanningService.getRecentCapacityPlans(days);
    }

    @GetMapping("/alerts")
    public List<CapacityPlan> getCapacityAlerts() {
        return capacityPlanningService.getAlertsForCapacity();
    }

    @GetMapping("/critical")
    public List<CapacityPlan> getCriticalCapacityPlans() {
        return capacityPlanningService.getCriticalCapacityPlans();
    }

    @GetMapping("/service/{serviceName}")
    public ResponseEntity<CapacityPlan> getLatestCapacityPlan(@PathVariable String serviceName) {
        CapacityPlan plan = capacityPlanningService.getLatestCapacityPlan(serviceName);
        if (plan != null) {
            return ResponseEntity.ok(plan);
        }
        return ResponseEntity.notFound().build();
    }

    @PostMapping("/generate/{serviceName}")
    public ResponseEntity<CapacityPlan> generateCapacityPlan(@PathVariable String serviceName) {
        return serviceInfoRepository.findByServiceName(serviceName)
                .map(service -> {
                    CapacityPlan plan = capacityPlanningService.generateCapacityPlan(service);
                    if (plan != null) {
                        return ResponseEntity.ok(plan);
                    }
                    return ResponseEntity.noContent().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Object>> getCapacityStatistics() {
        List<CapacityPlan> allPlans = capacityPlanningService.getRecentCapacityPlans(7);
        
        long criticalCount = allPlans.stream()
                .filter(p -> p.getStatus() == CapacityPlan.CapacityStatus.CRITICAL)
                .count();
        long needsExpansionCount = allPlans.stream()
                .filter(p -> p.getStatus() == CapacityPlan.CapacityStatus.NEEDS_EXPANSION)
                .count();
        long warningCount = allPlans.stream()
                .filter(p -> p.getStatus() == CapacityPlan.CapacityStatus.WARNING)
                .count();
        long normalCount = allPlans.stream()
                .filter(p -> p.getStatus() == CapacityPlan.CapacityStatus.NORMAL)
                .count();
        long overProvisionedCount = allPlans.stream()
                .filter(p -> p.getStatus() == CapacityPlan.CapacityStatus.OVER_PROVISIONED)
                .count();

        double avgUtilization = allPlans.stream()
                .mapToDouble(CapacityPlan::getCurrentUtilization)
                .average()
                .orElse(0.0);

        double avgPredicted7d = allPlans.stream()
                .mapToDouble(CapacityPlan::getPredictedUtilization7d)
                .average()
                .orElse(0.0);

        return ResponseEntity.ok(Map.of(
            "totalPlans", allPlans.size(),
            "criticalPlans", criticalCount,
            "needsExpansionPlans", needsExpansionCount,
            "warningPlans", warningCount,
            "normalPlans", normalCount,
            "overProvisionedPlans", overProvisionedCount,
            "averageCurrentUtilization", avgUtilization,
            "averagePredictedUtilization7d", avgPredicted7d
        ));
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getCapacitySummary() {
        List<CapacityPlan> alerts = capacityPlanningService.getAlertsForCapacity();
        
        boolean needsAttention = !alerts.isEmpty();
        
        return ResponseEntity.ok(Map.of(
            "needsAttention", needsAttention,
            "alertCount", alerts.size(),
            "alerts", alerts
        ));
    }
}

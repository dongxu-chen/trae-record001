package com.tracing.optimizer.service.controller;

import com.tracing.optimizer.core.cost.CostModel;
import com.tracing.optimizer.service.service.SamplingRateService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/cost")
public class CostController {

    private final SamplingRateService service;

    public CostController(SamplingRateService service) {
        this.service = service;
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getCostSummary() {
        Map<String, Object> summary = service.getCostSummary();
        Map<String, Object> cpuCost = service.getCpuCostSummary();
        summary.put("cpuCost", cpuCost);
        return ResponseEntity.ok(summary);
    }

    @GetMapping("/projections")
    public ResponseEntity<Map<String, Object>> getCostProjections() {
        return ResponseEntity.ok(service.getCostProjections());
    }

    @GetMapping("/budget-status")
    public ResponseEntity<Map<String, Object>> getBudgetStatus() {
        Map<String, Object> summary = service.getCostSummary();
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("utilizationPercent", summary.get("utilizationPercent"));
        status.put("overBudget", summary.get("overBudget"));
        status.put("alertTriggered", summary.get("alertTriggered"));
        status.put("remainingBudget", summary.get("remainingBudget"));
        return ResponseEntity.ok(status);
    }

    @GetMapping("/cpu-summary")
    public ResponseEntity<Map<String, Object>> getCpuCostSummary() {
        return ResponseEntity.ok(service.getCpuCostSummary());
    }

    @GetMapping("/assessment/{serviceName}")
    public ResponseEntity<CostModel.ComprehensiveCostAssessment> getCostAssessment(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "0.1") double proposedRate) {
        CostModel.ComprehensiveCostAssessment assessment =
                service.getCostAssessment(serviceName, proposedRate);
        if (assessment == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(assessment);
    }

    @GetMapping("/all-assessments")
    public ResponseEntity<Map<String, CostModel.ComprehensiveCostAssessment>> getAllCostAssessments() {
        return ResponseEntity.ok(service.getAllCostAssessments());
    }
}

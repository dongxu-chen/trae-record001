package com.tracing.optimizer.service.controller;

import com.tracing.optimizer.service.service.SamplingRateService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/enhancement")
public class EnhancementController {

    private final SamplingRateService samplingRateService;

    public EnhancementController(SamplingRateService samplingRateService) {
        this.samplingRateService = samplingRateService;
    }

    @GetMapping("/anomaly/stats")
    public ResponseEntity<Map<String, Object>> getAnomalyStats() {
        return ResponseEntity.ok(samplingRateService.getAnomalyEnhancementStats());
    }

    @GetMapping("/anomaly/service/{serviceName}/error-rate")
    public ResponseEntity<Double> getServiceErrorRate(@PathVariable String serviceName) {
        return ResponseEntity.ok(samplingRateService.getServiceErrorRate(serviceName));
    }

    @GetMapping("/anomaly/service/{serviceName}/boosted-rate")
    public ResponseEntity<Double> getBoostedSamplingRate(@PathVariable String serviceName) {
        return ResponseEntity.ok(samplingRateService.getBoostedSamplingRate(serviceName));
    }

    @PostMapping("/anomaly/check-force-sample")
    public ResponseEntity<Boolean> checkForceSample(
            @RequestParam String traceId,
            @RequestParam String serviceName,
            @RequestParam(defaultValue = "false") boolean hasError,
            @RequestParam(defaultValue = "200") int statusCode) {
        boolean shouldForce = samplingRateService.checkForceSample(traceId, serviceName, hasError, statusCode);
        return ResponseEntity.ok(shouldForce);
    }

    @GetMapping("/evaluation/service/{serviceName}")
    public ResponseEntity<Map<String, Object>> getServiceEvaluation(@PathVariable String serviceName) {
        return ResponseEntity.ok(samplingRateService.getSamplingEffectReport(serviceName));
    }

    @GetMapping("/evaluation/all")
    public ResponseEntity<Map<String, Map<String, Object>>> getAllEvaluations() {
        return ResponseEntity.ok(samplingRateService.getAllSamplingEffectReports());
    }

    @PostMapping("/evaluation/record-problem")
    public ResponseEntity<Void> recordProblem(
            @RequestParam String problemId,
            @RequestParam String serviceName,
            @RequestParam String type,
            @RequestParam boolean detected,
            @RequestParam double samplingRate) {
        samplingRateService.recordProblem(problemId, serviceName, type, detected, samplingRate);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/storage/heat-tier/{serviceName}")
    public ResponseEntity<Map<String, Object>> getHeatTierStats(@PathVariable String serviceName) {
        return ResponseEntity.ok(samplingRateService.getHeatTierStats(serviceName));
    }

    @GetMapping("/storage/heat-tiers")
    public ResponseEntity<Map<String, String>> getAllHeatTiers() {
        return ResponseEntity.ok(samplingRateService.getAllHeatTiers());
    }

    @PostMapping("/storage/adjust-rate")
    public ResponseEntity<Double> applyHeatTierAdjustment(
            @RequestParam String serviceName,
            @RequestParam double baseRate) {
        double adjusted = samplingRateService.applyHeatTierAdjustment(serviceName, baseRate);
        return ResponseEntity.ok(adjusted);
    }

    @PostMapping("/storage/record-heat/{serviceName}")
    public ResponseEntity<Void> recordServiceHeat(@PathVariable String serviceName) {
        samplingRateService.recordServiceHeat(serviceName);
        return ResponseEntity.ok().build();
    }
}

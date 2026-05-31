package com.tracing.optimizer.service.controller;

import com.tracing.optimizer.core.model.SamplingRate;
import com.tracing.optimizer.service.service.SamplingRateService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/sampling")
public class SamplingController {

    private final SamplingRateService service;

    public SamplingController(SamplingRateService service) {
        this.service = service;
    }

    @GetMapping("/rates")
    public ResponseEntity<Map<String, Object>> getAllRates() {
        Map<String, SamplingRate> rates = service.getAllSamplingRates();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("rates", rates);
        response.put("totalServices", rates.size());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/rates/{serviceName}")
    public ResponseEntity<SamplingRate> getRate(@PathVariable String serviceName) {
        SamplingRate rate = service.getSamplingRate(serviceName);
        if (rate == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(rate);
    }

    @PutMapping("/rates/{serviceName}")
    public ResponseEntity<SamplingRate> updateRate(
            @PathVariable String serviceName,
            @RequestBody Map<String, Object> body) {
        double businessImportance = ((Number) body.getOrDefault("businessImportance", 0.5)).doubleValue();
        double errorRate = ((Number) body.getOrDefault("errorRate", 0.01)).doubleValue();
        double p99LatencyMs = ((Number) body.getOrDefault("p99LatencyMs", 500.0)).doubleValue();
        long requestRate = ((Number) body.getOrDefault("requestRate", 1000L)).longValue();

        SamplingRate rate = service.updateServiceRate(serviceName, businessImportance,
                errorRate, p99LatencyMs, requestRate);
        return ResponseEntity.ok(rate);
    }

    @PostMapping("/optimize")
    public ResponseEntity<Map<String, SamplingRate>> triggerOptimization() {
        Map<String, SamplingRate> rates = service.triggerOptimization();
        return ResponseEntity.ok(rates);
    }

    @GetMapping("/edge/{serviceName}")
    public ResponseEntity<Map<String, Object>> edgeSamplingDecision(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "random") String traceId,
            @RequestParam(defaultValue = "0.1") double globalRate) {
        boolean sampled = service.shouldSampleEdge(serviceName, traceId, globalRate);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceName", serviceName);
        result.put("traceId", traceId);
        result.put("sampled", sampled);
        result.put("globalRate", globalRate);
        return ResponseEntity.ok(result);
    }
}

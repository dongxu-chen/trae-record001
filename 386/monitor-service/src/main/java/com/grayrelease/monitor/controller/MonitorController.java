package com.grayrelease.monitor.controller;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.dto.MetricData;
import com.grayrelease.common.model.MetricThreshold;
import com.grayrelease.monitor.service.AnomalyDetectionService;
import com.grayrelease.monitor.service.DynamicBaselineAnalyzer;
import com.grayrelease.monitor.service.MetricsCollectorService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/monitor")
@RequiredArgsConstructor
public class MonitorController {

    private final MetricsCollectorService metricsCollectorService;
    private final AnomalyDetectionService anomalyDetectionService;
    private final DynamicBaselineAnalyzer dynamicBaselineAnalyzer;

    @GetMapping("/metrics/{serviceName}/{version}")
    public ResponseEntity<MetricData> getMetric(
            @PathVariable String serviceName,
            @PathVariable String version,
            @RequestParam MetricType metricType) {
        MetricData metric = metricsCollectorService.getLatestMetric(serviceName, version, metricType);
        if (metric == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(metric);
    }

    @PostMapping("/targets")
    public ResponseEntity<String> registerTarget(
            @RequestParam String targetId,
            @RequestParam String serviceName,
            @RequestParam String version,
            @RequestBody List<MetricThreshold> thresholds) {
        metricsCollectorService.registerTarget(targetId, serviceName, version, thresholds);
        return ResponseEntity.ok("Target registered: " + targetId);
    }

    @DeleteMapping("/targets/{targetId}")
    public ResponseEntity<String> unregisterTarget(@PathVariable String targetId) {
        metricsCollectorService.unregisterTarget(targetId);
        return ResponseEntity.ok("Target unregistered: " + targetId);
    }

    @PostMapping("/analyze")
    public ResponseEntity<AnomalyDetectionService.AnomalyReport> analyzeMetrics(
            @RequestParam String serviceName,
            @RequestParam String version,
            @RequestBody List<MetricThreshold> thresholds) {
        AnomalyDetectionService.AnomalyReport report =
                anomalyDetectionService.analyzeMetrics(serviceName, version, thresholds);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/baseline/{serviceName}/{version}")
    public ResponseEntity<Map<String, DynamicBaselineAnalyzer.BaselineResult>> getBaselines(
            @PathVariable String serviceName,
            @PathVariable String version) {
        Map<String, DynamicBaselineAnalyzer.BaselineResult> baselines =
                dynamicBaselineAnalyzer.getAllBaselines(serviceName, version);
        return ResponseEntity.ok(baselines);
    }

    @GetMapping("/baseline/{serviceName}/{version}/{metricType}")
    public ResponseEntity<DynamicBaselineAnalyzer.BaselineResult> getBaseline(
            @PathVariable String serviceName,
            @PathVariable String version,
            @PathVariable MetricType metricType) {
        DynamicBaselineAnalyzer.BaselineResult result =
                anomalyDetectionService.getBaseline(serviceName, version, metricType);
        return ResponseEntity.ok(result);
    }

    @DeleteMapping("/baseline/{serviceName}")
    public ResponseEntity<String> clearBaseline(@PathVariable String serviceName) {
        dynamicBaselineAnalyzer.clearAllHistory(serviceName);
        return ResponseEntity.ok("Baseline history cleared for service: " + serviceName);
    }
}
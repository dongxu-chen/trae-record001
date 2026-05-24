package com.abtest.controller;

import com.abtest.dto.*;
import com.abtest.entity.Experiment;
import com.abtest.service.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/experiments")
@RequiredArgsConstructor
public class ExperimentController {

    private final ExperimentService experimentService;
    private final BucketingService bucketingService;
    private final EventTrackingService eventTrackingService;
    private final ReportService reportService;
    private final MABService mabService;
    private final AutoStopService autoStopService;
    private final LayerService layerService;

    @PostMapping
    public ResponseEntity<Experiment> createExperiment(@Valid @RequestBody ExperimentDTO dto) {
        Experiment experiment = experimentService.createExperiment(dto);
        return ResponseEntity.ok(experiment);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Experiment> getExperiment(@PathVariable Long id) {
        return experimentService.getExperiment(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    public ResponseEntity<List<Experiment>> getAllExperiments(
        @RequestParam(required = false) Experiment.ExperimentStatus status) {
        List<Experiment> experiments;
        if (status != null) {
            experiments = experimentService.getExperimentsByStatus(status);
        } else {
            experiments = experimentService.getAllExperiments();
        }
        return ResponseEntity.ok(experiments);
    }

    @PostMapping("/{id}/start")
    public ResponseEntity<Experiment> startExperiment(@PathVariable Long id) {
        return ResponseEntity.ok(experimentService.startExperiment(id));
    }

    @PostMapping("/{id}/pause")
    public ResponseEntity<Experiment> pauseExperiment(@PathVariable Long id) {
        return ResponseEntity.ok(experimentService.pauseExperiment(id));
    }

    @PostMapping("/{id}/resume")
    public ResponseEntity<Experiment> resumeExperiment(@PathVariable Long id) {
        return ResponseEntity.ok(experimentService.resumeExperiment(id));
    }

    @PostMapping("/{id}/complete")
    public ResponseEntity<Experiment> completeExperiment(@PathVariable Long id) {
        return ResponseEntity.ok(experimentService.completeExperiment(id));
    }

    @PostMapping("/traffic")
    public ResponseEntity<Experiment> adjustTraffic(@Valid @RequestBody TrafficAdjustmentDTO dto) {
        return ResponseEntity.ok(experimentService.adjustTraffic(dto));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteExperiment(@PathVariable Long id) {
        experimentService.deleteExperiment(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{experimentId}/assign/{userId}")
    public ResponseEntity<BucketAssignmentDTO> assignUser(
        @PathVariable Long experimentId,
        @PathVariable String userId) {
        BucketAssignmentDTO assignment = bucketingService.assignUser(userId, experimentId);
        return ResponseEntity.ok(assignment);
    }

    @PostMapping("/events")
    public ResponseEntity<Void> trackEvent(@Valid @RequestBody EventDTO event) {
        eventTrackingService.trackEvent(event);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/events/batch")
    public ResponseEntity<Void> trackEvents(@Valid @RequestBody List<EventDTO> events) {
        eventTrackingService.trackEvents(events);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}/report")
    public ResponseEntity<Map<String, Object>> generateReport(@PathVariable Long id) {
        Map<String, Object> report = reportService.generateReport(id);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/{id}/report/metrics/{metricName}")
    public ResponseEntity<StatisticalResultDTO> getMetricReport(
        @PathVariable Long id,
        @PathVariable String metricName) {
        StatisticalResultDTO result = reportService.getMetricStatistics(id, metricName);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/trend")
    public ResponseEntity<Map<String, Object>> getTrendData(
        @PathVariable Long id,
        @RequestParam(defaultValue = "7") int days) {
        Map<String, Object> trend = reportService.getTrendData(id, days);
        return ResponseEntity.ok(trend);
    }

    @GetMapping("/{id}/mab/status")
    public ResponseEntity<Map<String, Object>> getMABStatus(@PathVariable Long id) {
        Map<String, Object> status = mabService.getMABStatus(id);
        return ResponseEntity.ok(status);
    }

    @PostMapping("/{id}/mab/update")
    public ResponseEntity<Void> updateMABTraffic(@PathVariable Long id) {
        mabService.updateTrafficAllocation(id);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}/autostop/check")
    public ResponseEntity<AutoStopService.AutoStopCheckResult> checkAutoStop(@PathVariable Long id) {
        AutoStopService.AutoStopCheckResult result = autoStopService.checkAndStopIfNeeded(id);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/layers")
    public ResponseEntity<com.abtest.entity.Layer> createLayer(@Valid @RequestBody LayerDTO dto) {
        com.abtest.entity.Layer layer = layerService.createLayer(dto);
        return ResponseEntity.ok(layer);
    }

    @GetMapping("/layers")
    public ResponseEntity<List<com.abtest.entity.Layer>> getAllLayers(
        @RequestParam(required = false, defaultValue = "true") Boolean activeOnly) {
        List<com.abtest.entity.Layer> layers;
        if (Boolean.TRUE.equals(activeOnly)) {
            layers = layerService.getActiveLayers();
        } else {
            layers = layerService.getAllLayers();
        }
        return ResponseEntity.ok(layers);
    }

    @GetMapping("/layers/{id}")
    public ResponseEntity<com.abtest.entity.Layer> getLayer(@PathVariable Long id) {
        return layerService.getLayer(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping("/layers/{id}")
    public ResponseEntity<com.abtest.entity.Layer> updateLayer(
        @PathVariable Long id,
        @Valid @RequestBody LayerDTO dto) {
        com.abtest.entity.Layer layer = layerService.updateLayer(id, dto);
        return ResponseEntity.ok(layer);
    }

    @DeleteMapping("/layers/{id}")
    public ResponseEntity<Void> deleteLayer(@PathVariable Long id) {
        layerService.deleteLayer(id);
        return ResponseEntity.noContent().build();
    }
}

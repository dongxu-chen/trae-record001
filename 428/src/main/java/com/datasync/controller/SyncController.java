package com.datasync.controller;

import com.datasync.config.SyncConfig;
import com.datasync.model.Checkpoint;
import com.datasync.model.SyncTopology;
import com.datasync.model.ValidationResult;
import com.datasync.model.Watermark;
import com.datasync.service.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/sync")
public class SyncController {

    private final CheckpointService checkpointService;
    private final FullSyncService fullSyncService;
    private final MetricsService metricsService;
    private final WatermarkManager watermarkManager;
    private final DataValidationService validationService;
    private final DynamicTableManager dynamicTableManager;
    private final TopologyService topologyService;

    public SyncController(CheckpointService checkpointService,
                          FullSyncService fullSyncService,
                          MetricsService metricsService,
                          WatermarkManager watermarkManager,
                          DataValidationService validationService,
                          DynamicTableManager dynamicTableManager,
                          TopologyService topologyService) {
        this.checkpointService = checkpointService;
        this.fullSyncService = fullSyncService;
        this.metricsService = metricsService;
        this.watermarkManager = watermarkManager;
        this.validationService = validationService;
        this.dynamicTableManager = dynamicTableManager;
        this.topologyService = topologyService;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("status", "running");
        status.put("checkpoint", checkpointService.getCurrentCheckpoint());
        return ResponseEntity.ok(status);
    }

    @GetMapping("/checkpoint")
    public ResponseEntity<Checkpoint> getCheckpoint() {
        return ResponseEntity.ok(checkpointService.getCurrentCheckpoint());
    }

    @PostMapping("/checkpoint/reset")
    public ResponseEntity<Map<String, String>> resetCheckpoint() {
        checkpointService.resetCheckpoint();
        Map<String, String> response = new HashMap<>();
        response.put("message", "Checkpoint reset successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/full-sync")
    public ResponseEntity<Map<String, String>> triggerFullSync() {
        log.info("Manual full sync triggered via API");
        new Thread(fullSyncService::performFullSync).start();
        Map<String, String> response = new HashMap<>();
        response.put("message", "Full sync triggered successfully");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/full-sync/status")
    public ResponseEntity<Map<String, Object>> getFullSyncStatus(
            @RequestParam String schema,
            @RequestParam String table) {
        Map<String, Object> status = new HashMap<>();
        status.put("schema", schema);
        status.put("table", table);
        status.put("complete", fullSyncService.isFullSyncComplete(schema, table));
        status.put("checkpoint", checkpointService.getTableCheckpoint(schema, table));
        return ResponseEntity.ok(status);
    }

    @PostMapping("/checkpoint/save")
    public ResponseEntity<Map<String, String>> forceSaveCheckpoint() {
        checkpointService.forceSave();
        Map<String, String> response = new HashMap<>();
        response.put("message", "Checkpoint saved successfully");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> healthCheck() {
        Map<String, String> health = new HashMap<>();
        health.put("status", "UP");
        return ResponseEntity.ok(health);
    }

    @GetMapping("/watermark")
    public ResponseEntity<Watermark> getWatermark() {
        return ResponseEntity.ok(watermarkManager.getWatermark());
    }

    @GetMapping("/watermark/table")
    public ResponseEntity<Watermark.TableWatermark> getTableWatermark(
            @RequestParam String schema,
            @RequestParam String table) {
        return ResponseEntity.ok(watermarkManager.getWatermark(schema, table));
    }

    @PostMapping("/watermark/reset")
    public ResponseEntity<Map<String, String>> resetWatermark(
            @RequestParam(required = false) String schema,
            @RequestParam(required = false) String table) {
        if (schema != null && table != null) {
            watermarkManager.resetWatermark(schema, table);
        } else {
            watermarkManager.resetAll();
        }
        Map<String, String> response = new HashMap<>();
        response.put("message", "Watermark reset successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/watermark/save")
    public ResponseEntity<Map<String, String>> forceSaveWatermark() {
        watermarkManager.forceSave();
        Map<String, String> response = new HashMap<>();
        response.put("message", "Watermark saved successfully");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/watermark/status")
    public ResponseEntity<Map<String, Object>> getWatermarkStatus(
            @RequestParam String schema,
            @RequestParam String table) {
        Map<String, Object> status = new HashMap<>();
        status.put("schema", schema);
        status.put("table", table);
        status.put("fullSyncCompleted", watermarkManager.isFullSyncCompleted(schema, table));
        status.put("canStartIncremental", watermarkManager.canStartIncremental(schema, table));
        status.put("watermark", watermarkManager.getWatermark(schema, table));
        return ResponseEntity.ok(status);
    }

    @PostMapping("/validate/{schema}/{table}")
    public ResponseEntity<Map<String, Object>> triggerValidation(@PathVariable String schema, @PathVariable String table) {
        try {
            ValidationResult result = validationService.validateTableAsync(schema, table);
            Map<String, Object> response = new HashMap<>();
            response.put("taskId", result.getValidationId());
            response.put("status", "STARTED");
            response.put("message", "Validation task started for " + schema + "." + table);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", "ERROR");
            response.put("message", e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @PostMapping("/validate/all")
    public ResponseEntity<Map<String, Object>> triggerAllValidation() {
        try {
            validationService.validateAllTablesAsync();
            Map<String, Object> response = new HashMap<>();
            response.put("status", "STARTED");
            response.put("message", "All validation tasks started");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", "ERROR");
            response.put("message", e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/validate/{schema}/{table}")
    public ResponseEntity<ValidationResult> getValidationResult(@PathVariable String schema, @PathVariable String table) {
        ValidationResult result = validationService.getLastValidationResult(schema, table);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/validate/history")
    public ResponseEntity<List<ValidationResult>> getValidationHistory() {
        return ResponseEntity.ok(validationService.getValidationHistory());
    }

    @PostMapping("/tables/refresh")
    public ResponseEntity<Map<String, Object>> refreshTables() {
        try {
            List<SyncConfig.TableMapping> newTables = dynamicTableManager.discoverNewTables();
            Map<String, Object> response = new HashMap<>();
            response.put("status", "SUCCESS");
            response.put("discovered", newTables.size());
            response.put("newTables", newTables);
            response.put("totalTables", dynamicTableManager.getAllTableMappings().size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", "ERROR");
            response.put("message", e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/tables")
    public ResponseEntity<List<SyncConfig.TableMapping>> getAllTables() {
        return ResponseEntity.ok(dynamicTableManager.getAllTableMappings());
    }

    @PostMapping("/tables")
    public ResponseEntity<Map<String, Object>> addTable(@RequestBody SyncConfig.TableMapping tableMapping) {
        try {
            boolean added = dynamicTableManager.addTableMapping(tableMapping);
            Map<String, Object> response = new HashMap<>();
            response.put("status", added ? "ADDED" : "ALREADY_EXISTS");
            response.put("tableMapping", tableMapping);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", "ERROR");
            response.put("message", e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @DeleteMapping("/tables/{schema}/{table}")
    public ResponseEntity<Map<String, Object>> removeTable(@PathVariable String schema, @PathVariable String table) {
        try {
            boolean removed = dynamicTableManager.removeTableMapping(schema, table);
            Map<String, Object> response = new HashMap<>();
            response.put("status", removed ? "REMOVED" : "NOT_FOUND");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("status", "ERROR");
            response.put("message", e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/topology")
    public ResponseEntity<SyncTopology> getTopology() {
        SyncTopology topology = topologyService.buildTopology();
        return ResponseEntity.ok(topology);
    }

    @GetMapping("/topology/summary")
    public ResponseEntity<Map<String, Object>> getTopologySummary() {
        return ResponseEntity.ok(topologyService.getTopologySummary());
    }
}

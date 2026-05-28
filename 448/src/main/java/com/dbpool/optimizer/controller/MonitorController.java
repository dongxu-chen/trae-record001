package com.dbpool.optimizer.controller;

import com.dbpool.optimizer.model.*;
import com.dbpool.optimizer.monitoring.AutoTuningEngine;
import com.dbpool.optimizer.monitoring.PoolMonitorService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.*;

@RestController
@RequestMapping("/api/monitor")
@CrossOrigin(origins = "*")
public class MonitorController {

    private final PoolMonitorService monitorService;
    private final AutoTuningEngine tuningEngine;
    private final ObjectMapper objectMapper;
    private final Set<SseEmitter> emitters = ConcurrentHashMap.newKeySet();
    private ScheduledExecutorService sseScheduler;

    public MonitorController(PoolMonitorService monitorService,
                              AutoTuningEngine tuningEngine,
                              ObjectMapper objectMapper) {
        this.monitorService = monitorService;
        this.tuningEngine = tuningEngine;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/start")
    public ResponseEntity<Map<String, String>> startMonitoring(@RequestBody MonitorStartRequest request) {
        monitorService.startMonitoring(request.getConfig(), request.getWorkload());
        startSsePush();
        return ResponseEntity.ok(Map.of("status", "started", "message", "监控已启动"));
    }

    @PostMapping("/stop")
    public ResponseEntity<Map<String, String>> stopMonitoring() {
        monitorService.stopMonitoring();
        stopSsePush();
        return ResponseEntity.ok(Map.of("status", "stopped", "message", "监控已停止"));
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getMonitorStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("monitoring", monitorService.isMonitoring());
        status.put("dynamicMaxPoolSize", monitorService.getDynamicMaxPoolSize());
        status.put("dynamicMinIdle", monitorService.getDynamicMinIdle());
        status.put("snapshotCount", monitorService.getRecentSnapshots(1).size());
        return ResponseEntity.ok(status);
    }

    @GetMapping("/stream")
    public SseEmitter stream() {
        SseEmitter emitter = new SseEmitter(60000L);
        emitters.add(emitter);

        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError(e -> emitters.remove(emitter));

        return emitter;
    }

    @GetMapping("/snapshots")
    public ResponseEntity<List<PoolMonitorSnapshot>> getSnapshots(
            @RequestParam(defaultValue = "60") int count) {
        return ResponseEntity.ok(monitorService.getRecentSnapshots(count));
    }

    @GetMapping("/latest")
    public ResponseEntity<PoolMonitorSnapshot> getLatestSnapshot() {
        PoolMonitorSnapshot snapshot = monitorService.getLatestSnapshot();
        if (snapshot == null) return ResponseEntity.noContent().build();
        return ResponseEntity.ok(snapshot);
    }

    @PostMapping("/tuning/evaluate")
    public ResponseEntity<AutoTuningDecision> evaluateTuning() {
        AutoTuningDecision decision = tuningEngine.evaluate();
        if (decision == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(decision);
    }

    @PostMapping("/tuning/apply")
    public ResponseEntity<Map<String, String>> applyTuning(@RequestBody AutoTuningDecision decision) {
        monitorService.applyTuning(decision);
        return ResponseEntity.ok(Map.of("status", "applied",
                "parameter", decision.getParameter(),
                "newValue", String.valueOf(decision.getNewValue())));
    }

    @PostMapping("/tuning/auto-step")
    public ResponseEntity<AutoTuningDecision> autoTuneStep() {
        AutoTuningDecision decision = tuningEngine.evaluate();
        if (decision != null) {
            monitorService.applyTuning(decision);
        }
        return ResponseEntity.ok(decision);
    }

    @GetMapping("/tuning/history")
    public ResponseEntity<List<AutoTuningDecision>> getTuningHistory() {
        return ResponseEntity.ok(monitorService.getTuningHistory());
    }

    @GetMapping("/tuning/policy")
    public ResponseEntity<AutoTuningPolicy> getTuningPolicy() {
        return ResponseEntity.ok(tuningEngine.getPolicy());
    }

    @PutMapping("/tuning/policy")
    public ResponseEntity<Map<String, String>> updateTuningPolicy(@RequestBody AutoTuningPolicy policy) {
        tuningEngine.updatePolicy(policy);
        return ResponseEntity.ok(Map.of("status", "updated"));
    }

    @GetMapping("/slow-sql")
    public ResponseEntity<List<SlowSqlRecord>> getSlowSqlRecords(
            @RequestParam(defaultValue = "50") int limit) {
        return ResponseEntity.ok(monitorService.getSlowSqlRecords(limit));
    }

    @GetMapping("/slow-sql/analysis")
    public ResponseEntity<SlowSqlAnalysis> analyzeSlowSql() {
        return ResponseEntity.ok(monitorService.analyzeSlowSql());
    }

    @GetMapping("/alerts")
    public ResponseEntity<List<ConnectionLeakAlert>> getAlerts() {
        return ResponseEntity.ok(monitorService.getActiveAlerts());
    }

    @PostMapping("/alerts/{alertId}/acknowledge")
    public ResponseEntity<Map<String, String>> acknowledgeAlert(@PathVariable String alertId) {
        monitorService.acknowledgeAlert(alertId);
        return ResponseEntity.ok(Map.of("status", "acknowledged"));
    }

    private void startSsePush() {
        if (sseScheduler != null && !sseScheduler.isShutdown()) return;
        sseScheduler = Executors.newSingleThreadScheduledExecutor();
        sseScheduler.scheduleAtFixedRate(this::pushMonitorData, 0, 1, TimeUnit.SECONDS);
    }

    private void stopSsePush() {
        if (sseScheduler != null) {
            sseScheduler.shutdownNow();
        }
        emitters.forEach(emitter -> {
            try {
                emitter.complete();
            } catch (Exception ignored) {}
        });
        emitters.clear();
    }

    private void pushMonitorData() {
        if (!monitorService.isMonitoring() || emitters.isEmpty()) return;

        PoolMonitorSnapshot snapshot = monitorService.getLatestSnapshot();
        if (snapshot == null) return;

        AutoTuningDecision tuning = tuningEngine.evaluate();
        if (tuning != null) {
            monitorService.applyTuning(tuning);
        }

        List<ConnectionLeakAlert> alerts = monitorService.getActiveAlerts().stream()
                .filter(a -> !a.isAcknowledged())
                .toList();

        Map<String, Object> payload = new HashMap<>();
        payload.put("snapshot", snapshot);
        payload.put("dynamicMaxPoolSize", monitorService.getDynamicMaxPoolSize());
        payload.put("dynamicMinIdle", monitorService.getDynamicMinIdle());
        payload.put("tuningDecision", tuning);
        payload.put("activeAlerts", alerts);

        List<SseEmitter> deadEmitters = new ArrayList<>();
        for (SseEmitter emitter : emitters) {
            try {
                String json = objectMapper.writeValueAsString(payload);
                emitter.send(SseEmitter.event().name("monitor").data(json));
            } catch (IOException e) {
                deadEmitters.add(emitter);
            }
        }
        emitters.removeAll(deadEmitters);
    }

    public static class MonitorStartRequest {
        private PoolConfig config;
        private WorkloadProfile workload;

        public PoolConfig getConfig() { return config; }
        public void setConfig(PoolConfig config) { this.config = config; }
        public WorkloadProfile getWorkload() { return workload; }
        public void setWorkload(WorkloadProfile workload) { this.workload = workload; }
    }
}

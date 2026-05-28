package com.mqmonitor.api;

import com.mqmonitor.common.model.MessageTrace;
import com.mqmonitor.common.tracing.MessageTraceManager;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/traces")
@CrossOrigin(origins = "*")
public class TraceController {

    private final MessageTraceManager traceManager;

    public TraceController() {
        this.traceManager = MessageTraceManager.getInstance();
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("timestamp", System.currentTimeMillis());
        stats.putAll(traceManager.getStats());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/{traceId}")
    public ResponseEntity<MessageTrace> getTrace(@PathVariable String traceId) {
        MessageTrace trace = traceManager.getTrace(traceId);
        if (trace == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(trace);
    }

    @GetMapping("/topic/{topic}")
    public ResponseEntity<List<MessageTrace>> getTracesByTopic(
            @PathVariable String topic,
            @RequestParam(defaultValue = "100") int limit) {
        List<MessageTrace> traces = traceManager.getTracesByTopic(topic, limit);
        return ResponseEntity.ok(traces);
    }

    @GetMapping("/consumer/{consumerGroup}")
    public ResponseEntity<List<MessageTrace>> getTracesByConsumerGroup(
            @PathVariable String consumerGroup,
            @RequestParam(defaultValue = "100") int limit) {
        List<MessageTrace> traces = traceManager.getTracesByConsumerGroup(consumerGroup, limit);
        return ResponseEntity.ok(traces);
    }

    @GetMapping("/slow")
    public ResponseEntity<List<MessageTrace>> getSlowTraces(
            @RequestParam(defaultValue = "5000") long minLatencyMs,
            @RequestParam(defaultValue = "50") int limit) {
        List<MessageTrace> traces = traceManager.getSlowTraces(minLatencyMs, limit);
        return ResponseEntity.ok(traces);
    }

    @GetMapping("/failed")
    public ResponseEntity<List<MessageTrace>> getFailedTraces(
            @RequestParam(defaultValue = "50") int limit) {
        List<MessageTrace> traces = traceManager.getFailedTraces(limit);
        return ResponseEntity.ok(traces);
    }

    @GetMapping("/active")
    public ResponseEntity<List<MessageTrace>> getActiveTraces() {
        List<MessageTrace> traces = traceManager.getActiveTraces();
        return ResponseEntity.ok(traces);
    }

    @GetMapping("/stuck")
    public ResponseEntity<List<MessageTrace>> getStuckTraces(
            @RequestParam(defaultValue = "300000") long ageMs) {
        List<MessageTrace> traces = traceManager.getActiveTracesOlderThan(ageMs);
        return ResponseEntity.ok(traces);
    }

    @PostMapping("/config")
    public ResponseEntity<Map<String, Object>> updateConfig(
            @RequestParam(required = false) Double sampleRate,
            @RequestParam(required = false) Integer maxTraces,
            @RequestParam(required = false) Long ttlMs,
            @RequestParam(required = false) Boolean enabled) {
        if (sampleRate != null) {
            traceManager.setSampleRate(sampleRate);
        }
        if (maxTraces != null) {
            traceManager.setMaxTraces(maxTraces);
        }
        if (ttlMs != null) {
            traceManager.setTraceTtlMs(ttlMs);
        }
        if (enabled != null) {
            traceManager.setEnabled(enabled);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("sampleRate", traceManager.getStats().get("sampleRate"));
        response.put("enabled", traceManager.isEnabled());
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/all")
    public ResponseEntity<Map<String, Object>> clearAllTraces() {
        traceManager.clearAll();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "All traces cleared");
        return ResponseEntity.ok(response);
    }
}

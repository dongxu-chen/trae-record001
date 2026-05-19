package com.logplatform.controller;

import com.logplatform.model.LogCluster;
import com.logplatform.model.LogTemplate;
import com.logplatform.model.TraceAnalysisResult;
import com.logplatform.service.LogMiningService;
import com.logplatform.service.RealtimeLogService;
import com.logplatform.service.TraceAnalysisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final LogMiningService logMiningService;
    private final TraceAnalysisService traceAnalysisService;
    private final RealtimeLogService realtimeLogService;

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getDashboardStats() {
        Map<String, Object> stats = logMiningService.getMiningStats();
        stats.put("activeWebSocketConnections", realtimeLogService.getActiveConnections());
        stats.put("realtimeBufferSize", realtimeLogService.getBufferSize());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/templates")
    public ResponseEntity<List<LogTemplate>> getTopTemplates(
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(logMiningService.getTopTemplates(limit));
    }

    @GetMapping("/templates/category/{category}")
    public ResponseEntity<List<LogTemplate>> getTemplatesByCategory(
            @PathVariable String category) {
        return ResponseEntity.ok(logMiningService.getTemplatesByCategory(category));
    }

    @GetMapping("/clusters")
    public ResponseEntity<List<LogCluster>> getTopClusters(
            @RequestParam(defaultValue = "10") int limit) {
        return ResponseEntity.ok(logMiningService.getTopClusters(limit));
    }

    @PostMapping("/mining/analyze")
    public ResponseEntity<Map<String, Object>> triggerAnalysis() {
        new Thread(() -> {
            try {
                logMiningService.runAnalysis();
            } catch (Exception e) {
                log.error("Manual mining analysis failed", e);
            }
        }).start();
        return ResponseEntity.ok(Map.of(
                "status", "started",
                "message", "Log pattern analysis triggered"
        ));
    }

    @GetMapping("/trace/{traceId}")
    public ResponseEntity<TraceAnalysisResult> analyzeTrace(
            @PathVariable String traceId,
            @RequestParam(required = false) String startTime,
            @RequestParam(required = false) String endTime) {
        TraceAnalysisResult result = traceAnalysisService.analyzeTrace(traceId, startTime, endTime);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/traces")
    public ResponseEntity<Map<String, Object>> searchTraces(
            @RequestParam(required = false) String appName,
            @RequestParam(required = false) String level,
            @RequestParam(required = false) Long minDurationMs,
            @RequestParam(required = false) String startTime,
            @RequestParam(required = false) String endTime,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) throws Exception {
        return ResponseEntity.ok(traceAnalysisService.searchTraces(
                appName, level, minDurationMs, startTime, endTime, page, size));
    }

    @GetMapping("/realtime/info")
    public ResponseEntity<Map<String, Object>> getRealtimeInfo() {
        return ResponseEntity.ok(Map.of(
                "endpoint", "/ws/logs",
                "activeConnections", realtimeLogService.getActiveConnections(),
                "bufferSize", realtimeLogService.getBufferSize(),
                "filterParam", "?filter=keyword",
                "messageFormat", Map.of(
                        "type", "object",
                        "properties", Map.of(
                                "type", "string (log/pong)",
                                "data", "LogEntry object (when type=log)"
                        )
                ),
                "clientActions", Map.of(
                        "setFilter", "{\"action\":\"filter\",\"filter\":\"keyword\"}",
                        "ping", "{\"action\":\"ping\"}"
                )
        ));
    }
}

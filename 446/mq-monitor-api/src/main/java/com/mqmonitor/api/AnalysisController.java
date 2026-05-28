package com.mqmonitor.api;

import com.mqmonitor.analysis.MessageTypeAnalyzer;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.MessageTypeAnalysis;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/analysis")
@CrossOrigin(origins = "*")
public class AnalysisController {

    private final MessageTypeAnalyzer analyzer;

    public AnalysisController() {
        this.analyzer = MessageTypeAnalyzer.getInstance();
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("timestamp", System.currentTimeMillis());
        stats.putAll(analyzer.getStats());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/types")
    public ResponseEntity<List<Map<String, Object>>> getAllAnalyses() {
        List<Map<String, Object>> analyses = analyzer.getAllAnalyses();
        return ResponseEntity.ok(analyses);
    }

    @GetMapping("/types/{mqType}/{cluster}/{topic}/{messageType}")
    public ResponseEntity<MessageTypeAnalysis> getAnalysis(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestParam(required = false) String consumerGroup,
            @PathVariable String messageType) {
        MessageTypeAnalysis analysis = analyzer.getAnalysis(mqType, cluster, topic, consumerGroup, messageType);
        if (analysis == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(analysis);
    }

    @GetMapping("/types/topic/{mqType}/{cluster}/{topic}")
    public ResponseEntity<List<MessageTypeAnalysis>> getAnalysesByTopic(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic) {
        List<MessageTypeAnalysis> analyses = analyzer.getAnalysesByTopic(mqType, cluster, topic);
        return ResponseEntity.ok(analyses);
    }

    @GetMapping("/slow")
    public ResponseEntity<List<MessageTypeAnalysis>> getSlowMessageTypes(
            @RequestParam(defaultValue = "20") int limit) {
        List<MessageTypeAnalysis> analyses = analyzer.getSlowMessageTypes(limit);
        return ResponseEntity.ok(analyses);
    }

    @GetMapping("/anomalous")
    public ResponseEntity<List<MessageTypeAnalysis>> getAnomalousMessageTypes(
            @RequestParam(defaultValue = "0.5") double minAnomalyScore,
            @RequestParam(defaultValue = "20") int limit) {
        List<MessageTypeAnalysis> analyses = analyzer.getAnomalousMessageTypes(minAnomalyScore, limit);
        return ResponseEntity.ok(analyses);
    }

    @PostMapping("/config")
    public ResponseEntity<Map<String, Object>> updateConfig(
            @RequestParam(required = false) Long slowThresholdMs,
            @RequestParam(required = false) Boolean enabled) {
        if (slowThresholdMs != null) {
            analyzer.setSlowThresholdMs(slowThresholdMs);
        }
        if (enabled != null) {
            analyzer.setEnabled(enabled);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("slowThresholdMs", analyzer.getSlowThresholdMs());
        response.put("enabled", analyzer.isEnabled());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/header-mapping")
    public ResponseEntity<Map<String, Object>> registerHeaderMapping(
            @RequestParam String headerName,
            @RequestParam String typeKey) {
        analyzer.registerHeaderTypeMapping(headerName, typeKey);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Header mapping registered");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/type-pattern")
    public ResponseEntity<Map<String, Object>> registerTypePattern(
            @RequestParam String regex) {
        analyzer.registerTypePattern(regex);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Type pattern registered");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> start() {
        analyzer.start();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Message type analyzer started");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/stop")
    public ResponseEntity<Map<String, Object>> stop() {
        analyzer.stop();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Message type analyzer stopped");
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/all")
    public ResponseEntity<Map<String, Object>> clearAll() {
        analyzer.clearAll();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "All analysis data cleared");
        return ResponseEntity.ok(response);
    }
}

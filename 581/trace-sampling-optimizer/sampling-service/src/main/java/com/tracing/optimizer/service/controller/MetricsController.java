package com.tracing.optimizer.service.controller;

import com.tracing.optimizer.core.edge.EdgeSampler;
import com.tracing.optimizer.core.feedback.FeedbackLoop;
import com.tracing.optimizer.core.model.FeedbackSignal;
import com.tracing.optimizer.service.service.SamplingRateService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/feedback")
public class MetricsController {

    private final SamplingRateService service;

    public MetricsController(SamplingRateService service) {
        this.service = service;
    }

    @PostMapping("/signal")
    public ResponseEntity<Map<String, Object>> submitSignal(@RequestBody Map<String, Object> body) {
        FeedbackSignal signal = new FeedbackSignal();
        signal.setServiceName((String) body.get("serviceName"));
        signal.setSignalType(FeedbackSignal.SignalType.valueOf((String) body.get("signalType")));
        signal.setSeverity(((Number) body.getOrDefault("severity", 0.5)).doubleValue());
        signal.setDescription((String) body.getOrDefault("description", ""));
        if (body.containsKey("suggestedRate")) {
            signal.setSuggestedRate(((Number) body.get("suggestedRate")).doubleValue());
        }

        service.submitFeedback(signal);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "accepted");
        response.put("serviceName", signal.getServiceName());
        response.put("signalType", signal.getSignalType());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/analysis/{serviceName}")
    public ResponseEntity<FeedbackLoop.FeedbackAnalysis> getFeedbackAnalysis(
            @PathVariable String serviceName) {
        FeedbackLoop.FeedbackAnalysis analysis = service.getFeedbackAnalysis(serviceName);
        return ResponseEntity.ok(analysis);
    }

    @GetMapping("/agent-status")
    public ResponseEntity<Map<String, Object>> getAgentStatus() {
        return ResponseEntity.ok(service.getAgentStatus());
    }

    @GetMapping("/edge-sampler-status")
    public ResponseEntity<Map<String, Object>> getEdgeSamplerStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("edgeStats", service.getEdgeAsyncStatus());
        status.put("centralDecisions", service.getCentralDecisions());
        return ResponseEntity.ok(status);
    }

    @GetMapping("/edge-async-status")
    public ResponseEntity<Map<String, Object>> getEdgeAsyncStatus() {
        return ResponseEntity.ok(service.getEdgeAsyncStatus());
    }

    @PostMapping("/push-central-decisions")
    public ResponseEntity<Map<String, Object>> pushCentralDecisions() {
        service.pushCentralDecisions();
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "success");
        response.put("message", "Central decisions pushed to edge samplers");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/central-decisions")
    public ResponseEntity<Map<String, EdgeSampler.CentralDecision>> getCentralDecisions() {
        return ResponseEntity.ok(service.getCentralDecisions());
    }
}

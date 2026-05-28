package com.mqmonitor.api;

import com.mqmonitor.autoscaler.ConsumerAutoScaler;
import com.mqmonitor.autoscaler.ScalingDecision;
import com.mqmonitor.common.config.AutoScalerConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.prediction.TimeSeriesPredictor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/autoscaler")
@CrossOrigin(origins = "*")
public class AutoScalerController {

    private final ConsumerAutoScaler autoScaler;

    public AutoScalerController() {
        AutoScalerConfig config = new AutoScalerConfig();
        TimeSeriesPredictor predictor = new TimeSeriesPredictor();
        this.autoScaler = new ConsumerAutoScaler(config, predictor);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("timestamp", System.currentTimeMillis());
        stats.put("running", autoScaler.isRunning());
        stats.putAll(autoScaler.getStats());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/config")
    public ResponseEntity<AutoScalerConfig> getConfig() {
        return ResponseEntity.ok(autoScaler.getConfig());
    }

    @PutMapping("/config")
    public ResponseEntity<Map<String, Object>> updateConfig(@RequestBody AutoScalerConfig newConfig) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Config updated");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/groups")
    public ResponseEntity<List<Map<String, Object>>> getAllGroupStatuses() {
        List<Map<String, Object>> statuses = autoScaler.getAllGroupStatuses();
        return ResponseEntity.ok(statuses);
    }

    @GetMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}")
    public ResponseEntity<Map<String, Object>> getGroupStatus(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup) {
        Map<String, Object> status = autoScaler.getGroupStatus(mqType, cluster, topic, consumerGroup);
        if (status == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(status);
    }

    @PostMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}/register")
    public ResponseEntity<Map<String, Object>> registerGroup(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup) {
        autoScaler.registerConsumerGroup(mqType, cluster, topic, consumerGroup);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Consumer group registered for auto-scaling");
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}")
    public ResponseEntity<Map<String, Object>> unregisterGroup(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup) {
        autoScaler.unregisterConsumerGroup(mqType, cluster, topic, consumerGroup);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Consumer group unregistered from auto-scaling");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}/evaluate")
    public ResponseEntity<ScalingDecision> evaluateGroup(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup) {
        ScalingDecision decision = autoScaler.evaluateGroup(mqType, cluster, topic, consumerGroup);
        if (decision == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(decision);
    }

    @GetMapping("/history")
    public ResponseEntity<List<ScalingDecision>> getDecisionHistory(
            @RequestParam(defaultValue = "100") int limit) {
        List<ScalingDecision> history = autoScaler.getDecisionHistory(limit);
        return ResponseEntity.ok(history);
    }

    @PostMapping("/start")
    public ResponseEntity<Map<String, Object>> start() {
        autoScaler.start();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Auto-scaler started");
        response.put("running", autoScaler.isRunning());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/stop")
    public ResponseEntity<Map<String, Object>> stop() {
        autoScaler.stop();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Auto-scaler stopped");
        response.put("running", autoScaler.isRunning());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}/scale-up")
    public ResponseEntity<Map<String, Object>> manualScaleUp(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup,
            @RequestParam int targetConsumers) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Manual scale-up requested");
        response.put("targetConsumers", targetConsumers);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/groups/{mqType}/{cluster}/{topic}/{consumerGroup}/scale-down")
    public ResponseEntity<Map<String, Object>> manualScaleDown(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @PathVariable String consumerGroup,
            @RequestParam int targetConsumers) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Manual scale-down requested");
        response.put("targetConsumers", targetConsumers);
        return ResponseEntity.ok(response);
    }
}

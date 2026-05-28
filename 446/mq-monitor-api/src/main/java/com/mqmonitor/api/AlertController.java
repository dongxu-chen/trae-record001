package com.mqmonitor.api;

import com.mqmonitor.alert.AlertManager;
import com.mqmonitor.common.config.AlertConfig;
import com.mqmonitor.common.model.Alert;
import com.mqmonitor.collector.MetricsManager;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/alerts")
@CrossOrigin(origins = "*")
public class AlertController {

    private final AlertManager alertManager;
    private final MetricsManager metricsManager;

    public AlertController() {
        this.metricsManager = MetricsManager.getInstance();
        this.alertManager = AlertManager.getInstance(metricsManager.getAlertConfig());
    }

    @GetMapping
    public ResponseEntity<List<Alert>> getAlerts(
            @RequestParam(defaultValue = "false") boolean activeOnly) {
        List<Alert> alerts = activeOnly ? alertManager.getActiveAlerts() : alertManager.getAllAlerts();
        return ResponseEntity.ok(alerts);
    }

    @GetMapping("/active")
    public ResponseEntity<List<Alert>> getActiveAlerts() {
        return ResponseEntity.ok(alertManager.getActiveAlerts());
    }

    @PostMapping("/evaluate")
    public ResponseEntity<List<Alert>> evaluateAlerts() {
        List<Alert> newAlerts = alertManager.runDetection();
        return ResponseEntity.ok(newAlerts);
    }

    @GetMapping("/config")
    public ResponseEntity<AlertConfig> getAlertConfig() {
        return ResponseEntity.ok(alertManager.getAnomalyDetector().getAlertConfig());
    }

    @PutMapping("/config")
    public ResponseEntity<AlertConfig> updateAlertConfig(@RequestBody AlertConfig config) {
        metricsManager.setAlertConfig(config);
        return ResponseEntity.ok(config);
    }

    @GetMapping("/count")
    public ResponseEntity<Map<String, Object>> getAlertCounts() {
        List<Alert> allAlerts = alertManager.getAllAlerts();
        List<Alert> activeAlerts = alertManager.getActiveAlerts();

        Map<String, Long> levelCounts = new HashMap<>();
        Map<String, Long> typeCounts = new HashMap<>();

        for (Alert alert : activeAlerts) {
            String level = alert.getLevel().name();
            String type = alert.getType().name();
            levelCounts.put(level, levelCounts.getOrDefault(level, 0L) + 1);
            typeCounts.put(type, typeCounts.getOrDefault(type, 0L) + 1);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("totalAlerts", allAlerts.size());
        response.put("activeAlerts", activeAlerts.size());
        response.put("levelCounts", levelCounts);
        response.put("typeCounts", typeCounts);

        return ResponseEntity.ok(response);
    }
}

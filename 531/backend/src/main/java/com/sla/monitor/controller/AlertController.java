package com.sla.monitor.controller;

import com.sla.monitor.model.Alert;
import com.sla.monitor.service.AlertService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/alerts")
public class AlertController {

    private final AlertService alertService;

    public AlertController(AlertService alertService) {
        this.alertService = alertService;
    }

    @GetMapping
    public List<Alert> getAlerts(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) Boolean active,
            @RequestParam(defaultValue = "24") int hours) {
        
        if (serviceName != null) {
            return alertService.getAlertsForService(serviceName);
        } else if (Boolean.TRUE.equals(active)) {
            return alertService.getActiveAlerts();
        } else {
            return alertService.getRecentAlerts(hours);
        }
    }

    @GetMapping("/active")
    public List<Alert> getActiveAlerts() {
        return alertService.getActiveAlerts();
    }

    @GetMapping("/service/{serviceName}")
    public List<Alert> getAlertsForService(@PathVariable String serviceName) {
        return alertService.getAlertsForService(serviceName);
    }

    @PostMapping("/{alertId}/acknowledge")
    public ResponseEntity<Alert> acknowledgeAlert(@PathVariable Long alertId) {
        Alert alert = alertService.acknowledgeAlert(alertId);
        return alert != null ? ResponseEntity.ok(alert) : ResponseEntity.notFound().build();
    }

    @PostMapping("/{alertId}/resolve")
    public ResponseEntity<Alert> resolveAlert(@PathVariable Long alertId) {
        Alert alert = alertService.resolveAlert(alertId);
        return alert != null ? ResponseEntity.ok(alert) : ResponseEntity.notFound().build();
    }
}

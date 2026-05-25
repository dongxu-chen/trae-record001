package com.alert.controller;

import com.alert.dto.AlertAcknowledgeRequest;
import com.alert.dto.AlertRequest;
import com.alert.entity.AlertAggregation;
import com.alert.entity.AlertEvent;
import com.alert.entity.AlertHistory;
import com.alert.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/alerts")
@CrossOrigin(origins = "*")
public class AlertController {

    @Autowired
    private AlertService alertService;

    @PostMapping
    public ResponseEntity<AlertEvent> createAlert(@Validated @RequestBody AlertRequest request) {
        AlertEvent alert = alertService.createAlert(request);
        return ResponseEntity.ok(alert);
    }

    @GetMapping
    public ResponseEntity<List<AlertEvent>> getAllAlerts() {
        List<AlertEvent> alerts = alertService.getAllAlerts();
        return ResponseEntity.ok(alerts);
    }

    @GetMapping("/{alertId}")
    public ResponseEntity<AlertEvent> getAlertById(@PathVariable String alertId) {
        AlertEvent alert = alertService.getAlertById(alertId);
        return ResponseEntity.ok(alert);
    }

    @GetMapping("/{alertId}/history")
    public ResponseEntity<List<AlertHistory>> getAlertHistory(@PathVariable String alertId) {
        List<AlertHistory> history = alertService.getAlertHistory(alertId);
        return ResponseEntity.ok(history);
    }

    @PostMapping("/{alertId}/acknowledge")
    public ResponseEntity<AlertEvent> acknowledgeAlert(
            @PathVariable String alertId,
            @Validated @RequestBody AlertAcknowledgeRequest request) {
        AlertEvent alert = alertService.acknowledgeAlert(alertId, request);
        return ResponseEntity.ok(alert);
    }

    @PostMapping("/{alertId}/process")
    public ResponseEntity<AlertEvent> processAlert(
            @PathVariable String alertId,
            @RequestBody Map<String, String> body) {
        String operator = body.getOrDefault("operator", "SYSTEM");
        String remark = body.get("remark");
        AlertEvent alert = alertService.processAlert(alertId, operator, remark);
        return ResponseEntity.ok(alert);
    }

    @PostMapping("/{alertId}/resolve")
    public ResponseEntity<AlertEvent> resolveAlert(
            @PathVariable String alertId,
            @RequestBody Map<String, String> body) {
        String operator = body.getOrDefault("operator", "SYSTEM");
        String remark = body.get("remark");
        AlertEvent alert = alertService.resolveAlert(alertId, operator, remark);
        return ResponseEntity.ok(alert);
    }

    @PostMapping("/{alertId}/close")
    public ResponseEntity<AlertEvent> closeAlert(
            @PathVariable String alertId,
            @RequestBody Map<String, String> body) {
        String operator = body.getOrDefault("operator", "SYSTEM");
        String remark = body.get("remark");
        AlertEvent alert = alertService.closeAlert(alertId, operator, remark);
        return ResponseEntity.ok(alert);
    }

    @GetMapping("/aggregations")
    public ResponseEntity<List<AlertAggregation>> getAllAggregations() {
        List<AlertAggregation> aggregations = alertService.getAllAggregations();
        return ResponseEntity.ok(aggregations);
    }
}

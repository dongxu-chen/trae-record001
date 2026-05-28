package com.configcenter.server.controller;

import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.service.AuditLogService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/config/audit")
public class AuditLogController {

    @Autowired
    private AuditLogService auditLogService;

    @GetMapping
    public ResponseEntity<List<ConfigAuditLog>> getAuditLogs(
            @RequestParam(required = false) String application,
            @RequestParam(required = false) String profile,
            @RequestParam(required = false) String label) {
        if (profile != null && label != null) {
            return ResponseEntity.ok(auditLogService.getAuditLogs(application, profile, label));
        }
        return ResponseEntity.ok(auditLogService.getAuditLogs(application));
    }

    @GetMapping("/time-range")
    public ResponseEntity<List<ConfigAuditLog>> getAuditLogsByTimeRange(
            @RequestParam String application,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime) {
        List<ConfigAuditLog> logs = auditLogService.getAuditLogsByTimeRange(
                application, startTime, endTime);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/operator/{operator}")
    public ResponseEntity<List<ConfigAuditLog>> getAuditLogsByOperator(
            @PathVariable String operator) {
        List<ConfigAuditLog> logs = auditLogService.getAuditLogsByOperator(operator);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/action/{action}")
    public ResponseEntity<List<ConfigAuditLog>> getAuditLogsByAction(
            @PathVariable ConfigAuditLog.ActionType action) {
        List<ConfigAuditLog> logs = auditLogService.getAuditLogsByAction(action);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/recent")
    public ResponseEntity<List<ConfigAuditLog>> getRecentAuditLogs(
            @RequestParam(defaultValue = "20") int limit) {
        List<ConfigAuditLog> logs = auditLogService.getRecentAuditLogs(limit);
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ConfigAuditLog> getAuditLogById(@PathVariable Long id) {
        ConfigAuditLog log = auditLogService.getAuditLogById(id);
        return log != null ? ResponseEntity.ok(log) : ResponseEntity.notFound().build();
    }
}

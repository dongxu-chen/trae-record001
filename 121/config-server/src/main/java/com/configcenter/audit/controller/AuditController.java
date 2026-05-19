package com.configcenter.audit.controller;

import com.configcenter.audit.entity.ConfigAuditLog;
import com.configcenter.audit.service.AuditService;
import com.configcenter.diff.entity.ConfigDiff;
import com.configcenter.diff.service.DiffService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/audit")
public class AuditController {

    @Autowired
    private AuditService auditService;

    @Autowired
    private DiffService diffService;

    @GetMapping("/logs")
    public ResponseEntity<List<ConfigAuditLog>> getAuditLogs(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) ConfigAuditLog.ChangeType type) {
        List<ConfigAuditLog> logs;
        if (type != null) {
            logs = auditService.getAuditLogsByType(type);
        } else {
            logs = auditService.getAuditLogs(serviceName);
        }
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/logs/{id}")
    public ResponseEntity<ConfigAuditLog> getAuditLog(@PathVariable String id) {
        return auditService.getAuditLog(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/logs/{id}/rollback")
    public ResponseEntity<ConfigAuditLog> rollback(
            @PathVariable String id,
            @RequestBody RollbackRequest request) {
        ConfigAuditLog rollbackLog = auditService.rollback(id, request.getRollbackBy());
        return ResponseEntity.ok(rollbackLog);
    }

    @GetMapping("/diff/{auditId}")
    public ResponseEntity<ConfigDiff> getDiffByAuditId(@PathVariable String auditId) {
        ConfigDiff diff = diffService.compareWithAudit(auditId);
        return ResponseEntity.ok(diff);
    }

    @GetMapping("/diff/compare")
    public ResponseEntity<ConfigDiff> compareTwoVersions(
            @RequestParam String serviceName,
            @RequestParam(required = false, defaultValue = "default") String profile,
            @RequestParam(required = false, defaultValue = "main") String label,
            @RequestParam String oldAuditId,
            @RequestParam String newAuditId) {
        ConfigDiff diff = diffService.compareTwoVersions(serviceName, profile, label, oldAuditId, newAuditId);
        return ResponseEntity.ok(diff);
    }

    @GetMapping("/diff/current-vs-proposed")
    public ResponseEntity<ConfigDiff> compareCurrentVsProposed(
            @RequestParam String serviceName,
            @RequestParam(required = false, defaultValue = "default") String profile,
            @RequestParam(required = false, defaultValue = "main") String label,
            @RequestBody Map<String, Object> proposedConfig) {
        ConfigDiff diff = diffService.compareWithCurrent(serviceName, profile, label, proposedConfig);
        return ResponseEntity.ok(diff);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getAuditStats() {
        return ResponseEntity.ok(auditService.getAuditStats());
    }

    public static class RollbackRequest {
        private String rollbackBy;

        public String getRollbackBy() { return rollbackBy; }
        public void setRollbackBy(String rollbackBy) { this.rollbackBy = rollbackBy; }
    }
}

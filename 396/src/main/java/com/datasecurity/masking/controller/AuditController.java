package com.datasecurity.masking.controller;

import com.datasecurity.masking.audit.AuditLog;
import com.datasecurity.masking.audit.AuditLogStore;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/audit")
public class AuditController {

    @Autowired
    private AuditLogStore auditLogStore;

    @GetMapping
    public ResponseEntity<Map<String, Object>> getAuditLogs(
            @RequestParam(required = false) String userId,
            @RequestParam(required = false) String databaseId,
            @RequestParam(required = false) String tableName,
            @RequestParam(required = false) String sensitiveType,
            @RequestParam(required = false) String operation,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date endTime,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        long start = startTime != null ? startTime.getTime() : 0;
        long end = endTime != null ? endTime.getTime() : System.currentTimeMillis();

        List<AuditLog> logs;

        if (userId != null) {
            logs = auditLogStore.findByUserId(userId, start, end);
        } else if (databaseId != null) {
            logs = auditLogStore.findByDatabaseId(databaseId, start, end);
        } else if (tableName != null) {
            logs = auditLogStore.findByTableName(tableName, start, end);
        } else if (sensitiveType != null) {
            logs = auditLogStore.findBySensitiveType(sensitiveType, start, end);
        } else if (operation != null) {
            logs = auditLogStore.findByOperation(operation, start, end);
        } else {
            logs = auditLogStore.findAll(start, end, page, size);
        }

        long total = auditLogStore.count(start, end);

        Map<String, Object> result = new HashMap<>();
        result.put("data", logs);
        result.put("total", total);
        result.put("page", page);
        result.put("size", size);

        return ResponseEntity.ok(result);
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<List<AuditLog>> getByUserId(
            @PathVariable String userId,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date endTime) {

        long start = startTime != null ? startTime.getTime() : 0;
        long end = endTime != null ? endTime.getTime() : System.currentTimeMillis();

        return ResponseEntity.ok(auditLogStore.findByUserId(userId, start, end));
    }

    @GetMapping("/database/{databaseId}")
    public ResponseEntity<List<AuditLog>> getByDatabaseId(
            @PathVariable String databaseId,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date endTime) {

        long start = startTime != null ? startTime.getTime() : 0;
        long end = endTime != null ? endTime.getTime() : System.currentTimeMillis();

        return ResponseEntity.ok(auditLogStore.findByDatabaseId(databaseId, start, end));
    }

    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Object>> getStatistics(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") Date endTime) {

        long start = startTime != null ? startTime.getTime() : 0;
        long end = endTime != null ? endTime.getTime() : System.currentTimeMillis();

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalQueries", auditLogStore.count(start, end));
        stats.put("queryCount", auditLogStore.findByOperation("QUERY", start, end).size());
        stats.put("exportCount", auditLogStore.findByOperation("EXPORT", start, end).size());
        stats.put("maskingCount", auditLogStore.findByOperation("MASKING", start, end).size());

        return ResponseEntity.ok(stats);
    }
}

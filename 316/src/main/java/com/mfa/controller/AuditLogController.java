package com.mfa.controller;

import com.mfa.entity.AuthLog;
import com.mfa.enums.AuthStatus;
import com.mfa.entity.User;
import com.mfa.service.AuditLogService;
import com.mfa.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogService auditLogService;
    private final UserService userService;

    @GetMapping("/logs/user")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Page<AuthLog>> getUserAuthLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        Pageable pageable = PageRequest.of(page, size);
        Page<AuthLog> logs = auditLogService.getUserAuthLogs(user.getId(), pageable);
        logs.forEach(log -> {
            if (log.getUser() != null) {
                log.getUser().setPasswordHash(null);
            }
        });
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/logs/session/{sessionId}")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<?> getSessionAuthLogs(@PathVariable String sessionId) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(auditLogService.getSessionAuthLogs(sessionId));
    }

    @GetMapping("/logs/all")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Page<AuthLog>> getAllAuthLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<AuthLog> logs = auditLogService.getAllAuthLogs(pageable);
        logs.forEach(log -> {
            if (log.getUser() != null) {
                log.getUser().setPasswordHash(null);
            }
        });
        return ResponseEntity.ok(logs);
    }

    @GetMapping("/logs/status/{status}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Page<AuthLog>> getAuthLogsByStatus(
            @PathVariable AuthStatus status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<AuthLog> logs = auditLogService.getAuthLogsByStatus(status, pageable);
        logs.forEach(log -> {
            if (log.getUser() != null) {
                log.getUser().setPasswordHash(null);
            }
        });
        return ResponseEntity.ok(logs);
    }
}

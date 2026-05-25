package com.filetransfer.controller;

import com.filetransfer.common.Result;
import com.filetransfer.entity.AuditLog;
import com.filetransfer.service.AuditLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/audit")
@RequiredArgsConstructor
public class AuditLogController {
    private final AuditLogService auditLogService;

    @GetMapping("/user/{userId}")
    public Result<Page<AuditLog>> getUserLogs(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<AuditLog> logs = auditLogService.getUserLogs(userId, page, size);
        return Result.success(logs);
    }
}

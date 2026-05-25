package com.filetransfer.service;

import com.filetransfer.entity.AuditLog;
import com.filetransfer.entity.User;
import com.filetransfer.repository.AuditLogRepository;
import com.filetransfer.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuditLogService {
    private final AuditLogRepository auditLogRepository;
    private final UserRepository userRepository;

    @Async
    public void logOperation(Long userId, String operation, Long fileId,
                             String fileName, Long fileSize, String status, String errorMessage) {
        try {
            AuditLog auditLog = new AuditLog();
            auditLog.setUserId(userId);
            auditLog.setOperation(operation);
            auditLog.setFileId(fileId);
            auditLog.setFileName(fileName);
            auditLog.setFileSize(fileSize);
            auditLog.setStatus(status);
            auditLog.setErrorMessage(errorMessage);

            if (userId != null) {
                userRepository.findById(userId).ifPresent(user ->
                        auditLog.setUsername(user.getUsername()));
            }

            auditLogRepository.save(auditLog);
        } catch (Exception e) {
            log.error("记录审计日志失败", e);
        }
    }

    public Page<AuditLog> getUserLogs(Long userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return auditLogRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }
}

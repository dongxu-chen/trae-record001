package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.repository.ConfigAuditLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AuditLogService {

    @Autowired
    private ConfigAuditLogRepository auditLogRepository;

    public List<ConfigAuditLog> getAuditLogs(String application) {
        if (application == null || application.isEmpty()) {
            return auditLogRepository.findAll();
        }
        return auditLogRepository.findByApplicationOrderByCreatedAtDesc(application);
    }

    public List<ConfigAuditLog> getAuditLogs(String application, String profile, String label) {
        return auditLogRepository.findByApplicationAndProfileAndLabelOrderByCreatedAtDesc(
                application, profile, label);
    }

    public List<ConfigAuditLog> getAuditLogsByTimeRange(String application,
                                                         LocalDateTime startTime,
                                                         LocalDateTime endTime) {
        return auditLogRepository.findByApplicationAndTimeRange(application, startTime, endTime);
    }

    public List<ConfigAuditLog> getAuditLogsByOperator(String operator) {
        return auditLogRepository.findByOperator(operator);
    }

    public List<ConfigAuditLog> getAuditLogsByAction(ConfigAuditLog.ActionType action) {
        return auditLogRepository.findByActionOrderByCreatedAtDesc(action);
    }

    public List<ConfigAuditLog> getRecentAuditLogs(int limit) {
        List<ConfigAuditLog> allLogs = auditLogRepository.findAll();
        if (allLogs.size() > limit) {
            return allLogs.subList(0, limit);
        }
        return allLogs;
    }

    public ConfigAuditLog getAuditLogById(Long id) {
        return auditLogRepository.findById(id).orElse(null);
    }
}

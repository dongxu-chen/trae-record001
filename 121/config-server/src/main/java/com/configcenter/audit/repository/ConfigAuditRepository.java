package com.configcenter.audit.repository;

import com.configcenter.audit.entity.ConfigAuditLog;
import com.configcenter.common.repository.InMemoryRepository;
import org.springframework.stereotype.Repository;

import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@Repository
public class ConfigAuditRepository extends InMemoryRepository<ConfigAuditLog, String> {

    public List<ConfigAuditLog> findByServiceName(String serviceName) {
        return storage.values().stream()
                .filter(log -> serviceName.equals(log.getServiceName()))
                .sorted(Comparator.comparing(ConfigAuditLog::getChangedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ConfigAuditLog> findByServiceNameAndProfile(String serviceName, String profile) {
        return storage.values().stream()
                .filter(log -> serviceName.equals(log.getServiceName()) && profile.equals(log.getProfile()))
                .sorted(Comparator.comparing(ConfigAuditLog::getChangedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ConfigAuditLog> findByChangeType(ConfigAuditLog.ChangeType changeType) {
        return storage.values().stream()
                .filter(log -> changeType == log.getChangeType())
                .sorted(Comparator.comparing(ConfigAuditLog::getChangedAt).reversed())
                .collect(Collectors.toList());
    }

    public List<ConfigAuditLog> findAllOrderByChangedAtDesc() {
        return storage.values().stream()
                .sorted(Comparator.comparing(ConfigAuditLog::getChangedAt).reversed())
                .collect(Collectors.toList());
    }
}

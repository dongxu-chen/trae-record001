package com.configcenter.audit.service;

import com.configcenter.audit.entity.ConfigAuditLog;
import com.configcenter.audit.repository.ConfigAuditRepository;
import com.configcenter.diff.entity.ConfigDiff;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.config.environment.Environment;
import org.springframework.cloud.config.server.environment.EnvironmentRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class AuditService {

    private static final Logger logger = LoggerFactory.getLogger(AuditService.class);

    @Autowired
    private ConfigAuditRepository auditRepository;

    @Autowired
    private EnvironmentRepository environmentRepository;

    public ConfigAuditLog logChange(ConfigAuditLog.ChangeType changeType,
                                    String serviceName,
                                    String profile,
                                    String label,
                                    Map<String, Object> oldConfig,
                                    Map<String, Object> newConfig,
                                    String changedBy,
                                    String changeReason) {

        ConfigAuditLog log = new ConfigAuditLog();
        log.setId("AUD-" + System.currentTimeMillis());
        log.setChangeType(changeType);
        log.setServiceName(serviceName);
        log.setProfile(profile);
        log.setLabel(label);
        log.setOldVersion(oldConfig != null ? "v-" + (System.currentTimeMillis() - 1000) : null);
        log.setNewVersion("v-" + System.currentTimeMillis());
        log.setOldConfig(oldConfig != null ? oldConfig : new HashMap<>());
        log.setNewConfig(newConfig != null ? newConfig : new HashMap<>());
        log.setChangedBy(changedBy);
        log.setChangedAt(LocalDateTime.now());
        log.setChangeReason(changeReason);
        log.setRolledBack(false);

        auditRepository.save(log.getId(), log);
        logger.info("Logged config change: {} for service: {}", log.getId(), serviceName);
        return log;
    }

    public ConfigAuditLog rollback(String auditId, String rollbackBy) {
        ConfigAuditLog log = auditRepository.findById(auditId)
                .orElseThrow(() -> new RuntimeException("Audit log not found: " + auditId));

        if (log.isRolledBack()) {
            throw new RuntimeException("This change has already been rolled back");
        }

        Map<String, Object> oldConfig = log.getOldConfig();
        Map<String, Object> currentConfig = fetchCurrentConfig(log.getServiceName(), log.getProfile(), log.getLabel());

        ConfigAuditLog rollbackLog = logChange(
                ConfigAuditLog.ChangeType.ROLLBACK,
                log.getServiceName(),
                log.getProfile(),
                log.getLabel(),
                currentConfig,
                oldConfig,
                rollbackBy,
                "Rollback from " + auditId
        );

        log.setRolledBack(true);
        auditRepository.save(log.getId(), log);

        logger.info("Rolled back config change: {} by {}", auditId, rollbackBy);
        return rollbackLog;
    }

    public Optional<ConfigAuditLog> getAuditLog(String id) {
        return auditRepository.findById(id);
    }

    public List<ConfigAuditLog> getAuditLogs(String serviceName) {
        if (serviceName != null && !serviceName.isEmpty()) {
            return auditRepository.findByServiceName(serviceName);
        }
        return auditRepository.findAllOrderByChangedAtDesc();
    }

    public List<ConfigAuditLog> getAuditLogsByType(ConfigAuditLog.ChangeType changeType) {
        return auditRepository.findByChangeType(changeType);
    }

    public Map<String, Object> fetchCurrentConfig(String serviceName, String profile, String label) {
        Map<String, Object> configMap = new HashMap<>();
        try {
            Environment env = environmentRepository.findOne(serviceName, profile, label, false);
            if (env != null && env.getPropertySources() != null) {
                env.getPropertySources().forEach(source -> {
                    if (source.getSource() instanceof Map) {
                        configMap.putAll((Map) source.getSource());
                    }
                });
            }
        } catch (Exception e) {
            logger.error("Error fetching current config: {}/{}/{}", serviceName, profile, label, e);
        }
        return configMap;
    }

    public Map<String, Object> getAuditStats() {
        Map<String, Object> stats = new HashMap<>();
        List<ConfigAuditLog> allLogs = auditRepository.findAllOrderByChangedAtDesc();

        stats.put("totalChanges", allLogs.size());
        stats.put("rollbackCount", allLogs.stream().filter(ConfigAuditLog::isRolledBack).count());

        Map<String, Long> typeStats = new HashMap<>();
        for (ConfigAuditLog.ChangeType type : ConfigAuditLog.ChangeType.values()) {
            long count = allLogs.stream().filter(l -> type == l.getChangeType()).count();
            typeStats.put(type.name(), count);
        }
        stats.put("changeTypeStats", typeStats);

        Set<String> services = new HashSet<>();
        allLogs.forEach(l -> services.add(l.getServiceName()));
        stats.put("affectedServices", services.size());

        return stats;
    }
}

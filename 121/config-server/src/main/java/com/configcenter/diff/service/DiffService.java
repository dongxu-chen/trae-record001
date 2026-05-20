package com.configcenter.diff.service;

import com.configcenter.audit.entity.ConfigAuditLog;
import com.configcenter.audit.repository.ConfigAuditRepository;
import com.configcenter.diff.entity.ConfigDiff;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.config.environment.Environment;
import org.springframework.cloud.config.server.environment.EnvironmentRepository;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class DiffService {

    private static final Logger logger = LoggerFactory.getLogger(DiffService.class);

    @Autowired
    private EnvironmentRepository environmentRepository;

    @Autowired
    private ConfigAuditRepository auditRepository;

    public ConfigDiff compareWithCurrent(String serviceName, String profile, String label,
                                         Map<String, Object> targetConfig) {
        Map<String, Object> currentConfig = fetchCurrentConfig(serviceName, profile, label);
        return computeDiff(serviceName, profile, label, currentConfig, targetConfig, "current", "proposed");
    }

    public ConfigDiff compareWithAudit(String auditId) {
        ConfigAuditLog auditLog = auditRepository.findById(auditId)
                .orElseThrow(() -> new RuntimeException("Audit log not found: " + auditId));

        return computeDiff(
                auditLog.getServiceName(),
                auditLog.getProfile(),
                auditLog.getLabel(),
                auditLog.getOldConfig(),
                auditLog.getNewConfig(),
                auditLog.getOldVersion(),
                auditLog.getNewVersion()
        );
    }

    public ConfigDiff compareTwoVersions(String serviceName, String profile, String label,
                                         String oldAuditId, String newAuditId) {
        ConfigAuditLog oldLog = auditRepository.findById(oldAuditId)
                .orElseThrow(() -> new RuntimeException("Old audit log not found: " + oldAuditId));
        ConfigAuditLog newLog = auditRepository.findById(newAuditId)
                .orElseThrow(() -> new RuntimeException("New audit log not found: " + newAuditId));

        return computeDiff(
                serviceName, profile, label,
                oldLog.getNewConfig(), newLog.getNewConfig(),
                oldLog.getNewVersion(), newLog.getNewVersion()
        );
    }

    private ConfigDiff computeDiff(String serviceName, String profile, String label,
                                   Map<String, Object> oldConfig, Map<String, Object> newConfig,
                                   String oldVersion, String newVersion) {
        ConfigDiff diff = new ConfigDiff();
        diff.setServiceName(serviceName);
        diff.setProfile(profile);
        diff.setLabel(label);
        diff.setOldVersion(oldVersion);
        diff.setNewVersion(newVersion);

        List<ConfigDiff.DiffEntry> changes = new ArrayList<>();

        Set<String> allKeys = new HashSet<>();
        if (oldConfig != null) allKeys.addAll(oldConfig.keySet());
        if (newConfig != null) allKeys.addAll(newConfig.keySet());

        for (String key : allKeys) {
            Object oldVal = oldConfig != null ? oldConfig.get(key) : null;
            Object newVal = newConfig != null ? newConfig.get(key) : null;

            if (oldVal == null && newVal != null) {
                changes.add(createDiffEntry(key, ConfigDiff.DiffEntry.DiffType.ADDED, null, newVal));
            } else if (oldVal != null && newVal == null) {
                changes.add(createDiffEntry(key, ConfigDiff.DiffEntry.DiffType.DELETED, oldVal, null));
            } else if (oldVal != null && newVal != null && !Objects.equals(oldVal, newVal)) {
                changes.add(createDiffEntry(key, ConfigDiff.DiffEntry.DiffType.MODIFIED, oldVal, newVal));
            }
        }

        diff.setChanges(changes);
        diff.setTotalChanges(changes.size());
        diff.setAddedCount((int) changes.stream().filter(c -> c.getType() == ConfigDiff.DiffEntry.DiffType.ADDED).count());
        diff.setModifiedCount((int) changes.stream().filter(c -> c.getType() == ConfigDiff.DiffEntry.DiffType.MODIFIED).count());
        diff.setDeletedCount((int) changes.stream().filter(c -> c.getType() == ConfigDiff.DiffEntry.DiffType.DELETED).count());

        return diff;
    }

    private ConfigDiff.DiffEntry createDiffEntry(String key, ConfigDiff.DiffEntry.DiffType type,
                                                  Object oldValue, Object newValue) {
        ConfigDiff.DiffEntry entry = new ConfigDiff.DiffEntry();
        entry.setKey(key);
        entry.setType(type);
        entry.setOldValue(maskSensitiveValue(key, oldValue));
        entry.setNewValue(maskSensitiveValue(key, newValue));
        entry.setPath(key);
        return entry;
    }

    private Object maskSensitiveValue(String key, Object value) {
        if (value == null) return null;
        String lowerKey = key.toLowerCase();
        if (lowerKey.contains("password") || lowerKey.contains("secret") ||
                lowerKey.contains("token") || lowerKey.contains("key")) {
            return "****";
        }
        return value;
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

    public boolean isSensitiveChange(ConfigDiff diff) {
        return diff.getChanges().stream()
                .anyMatch(change -> {
                    String key = change.getKey().toLowerCase();
                    return key.contains("password") || key.contains("secret") ||
                            key.contains("token") || key.contains("key");
                });
    }

    public Map<String, Object> generateDiffSummary(ConfigDiff diff) {
        Map<String, Object> summary = new HashMap<>();
        summary.put("serviceName", diff.getServiceName());
        summary.put("totalChanges", diff.getTotalChanges());
        summary.put("addedCount", diff.getAddedCount());
        summary.put("modifiedCount", diff.getModifiedCount());
        summary.put("deletedCount", diff.getDeletedCount());
        summary.put("hasSensitiveChanges", isSensitiveChange(diff));

        List<String> changedKeys = new ArrayList<>();
        diff.getChanges().forEach(c -> changedKeys.add(c.getKey()));
        summary.put("changedKeys", changedKeys);

        return summary;
    }
}

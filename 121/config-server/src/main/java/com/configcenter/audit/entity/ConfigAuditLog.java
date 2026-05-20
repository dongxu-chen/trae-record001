package com.configcenter.audit.entity;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

public class ConfigAuditLog {

    private String id;
    private String serviceName;
    private String profile;
    private String label;
    private ChangeType changeType;
    private String oldVersion;
    private String newVersion;
    private Map<String, Object> oldConfig = new HashMap<>();
    private Map<String, Object> newConfig = new HashMap<>();
    private String changedBy;
    private LocalDateTime changedAt;
    private String changeReason;
    private String approvalId;
    private boolean rolledBack;
    private String rollbackFromId;

    public enum ChangeType {
        CREATE,
        UPDATE,
        DELETE,
        ROLLBACK,
        GRAYSCALE_PUBLISH,
        GRAYSCALE_COMPLETE
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getProfile() {
        return profile;
    }

    public void setProfile(String profile) {
        this.profile = profile;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public ChangeType getChangeType() {
        return changeType;
    }

    public void setChangeType(ChangeType changeType) {
        this.changeType = changeType;
    }

    public String getOldVersion() {
        return oldVersion;
    }

    public void setOldVersion(String oldVersion) {
        this.oldVersion = oldVersion;
    }

    public String getNewVersion() {
        return newVersion;
    }

    public void setNewVersion(String newVersion) {
        this.newVersion = newVersion;
    }

    public Map<String, Object> getOldConfig() {
        return oldConfig;
    }

    public void setOldConfig(Map<String, Object> oldConfig) {
        this.oldConfig = oldConfig;
    }

    public Map<String, Object> getNewConfig() {
        return newConfig;
    }

    public void setNewConfig(Map<String, Object> newConfig) {
        this.newConfig = newConfig;
    }

    public String getChangedBy() {
        return changedBy;
    }

    public void setChangedBy(String changedBy) {
        this.changedBy = changedBy;
    }

    public LocalDateTime getChangedAt() {
        return changedAt;
    }

    public void setChangedAt(LocalDateTime changedAt) {
        this.changedAt = changedAt;
    }

    public String getChangeReason() {
        return changeReason;
    }

    public void setChangeReason(String changeReason) {
        this.changeReason = changeReason;
    }

    public String getApprovalId() {
        return approvalId;
    }

    public void setApprovalId(String approvalId) {
        this.approvalId = approvalId;
    }

    public boolean isRolledBack() {
        return rolledBack;
    }

    public void setRolledBack(boolean rolledBack) {
        this.rolledBack = rolledBack;
    }

    public String getRollbackFromId() {
        return rollbackFromId;
    }

    public void setRollbackFromId(String rollbackFromId) {
        this.rollbackFromId = rollbackFromId;
    }
}

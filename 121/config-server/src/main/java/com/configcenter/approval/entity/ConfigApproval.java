package com.configcenter.approval.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ConfigApproval {

    private String id;
    private String serviceName;
    private String profile;
    private String label;
    private ApprovalStatus status;
    private ApprovalLevel currentLevel;
    private List<ApprovalRecord> approvalHistory = new ArrayList<>();
    private Map<String, Object> targetConfig = new HashMap<>();
    private String requestedBy;
    private LocalDateTime requestedAt;
    private String changeReason;
    private Map<String, Object> diffSummary = new HashMap<>();

    public enum ApprovalStatus {
        PENDING,
        IN_PROGRESS,
        APPROVED,
        REJECTED,
        CANCELLED,
        PUBLISHED
    }

    public enum ApprovalLevel {
        LEVEL1(1, "一级审批"),
        LEVEL2(2, "二级审批"),
        LEVEL3(3, "三级审批");

        private final int level;
        private final String description;

        ApprovalLevel(int level, String description) {
            this.level = level;
            this.description = description;
        }

        public int getLevel() {
            return level;
        }

        public String getDescription() {
            return description;
        }

        public ApprovalLevel next() {
            if (this == LEVEL1) return LEVEL2;
            if (this == LEVEL2) return LEVEL3;
            return null;
        }
    }

    public static class ApprovalRecord {
        private ApprovalLevel level;
        private String approver;
        private ApprovalAction action;
        private String comment;
        private LocalDateTime approvedAt;

        public enum ApprovalAction {
            APPROVE,
            REJECT,
            REQUEST_CHANGE
        }

        public ApprovalLevel getLevel() {
            return level;
        }

        public void setLevel(ApprovalLevel level) {
            this.level = level;
        }

        public String getApprover() {
            return approver;
        }

        public void setApprover(String approver) {
            this.approver = approver;
        }

        public ApprovalAction getAction() {
            return action;
        }

        public void setAction(ApprovalAction action) {
            this.action = action;
        }

        public String getComment() {
            return comment;
        }

        public void setComment(String comment) {
            this.comment = comment;
        }

        public LocalDateTime getApprovedAt() {
            return approvedAt;
        }

        public void setApprovedAt(LocalDateTime approvedAt) {
            this.approvedAt = approvedAt;
        }
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

    public ApprovalStatus getStatus() {
        return status;
    }

    public void setStatus(ApprovalStatus status) {
        this.status = status;
    }

    public ApprovalLevel getCurrentLevel() {
        return currentLevel;
    }

    public void setCurrentLevel(ApprovalLevel currentLevel) {
        this.currentLevel = currentLevel;
    }

    public List<ApprovalRecord> getApprovalHistory() {
        return approvalHistory;
    }

    public void setApprovalHistory(List<ApprovalRecord> approvalHistory) {
        this.approvalHistory = approvalHistory;
    }

    public Map<String, Object> getTargetConfig() {
        return targetConfig;
    }

    public void setTargetConfig(Map<String, Object> targetConfig) {
        this.targetConfig = targetConfig;
    }

    public String getRequestedBy() {
        return requestedBy;
    }

    public void setRequestedBy(String requestedBy) {
        this.requestedBy = requestedBy;
    }

    public LocalDateTime getRequestedAt() {
        return requestedAt;
    }

    public void setRequestedAt(LocalDateTime requestedAt) {
        this.requestedAt = requestedAt;
    }

    public String getChangeReason() {
        return changeReason;
    }

    public void setChangeReason(String changeReason) {
        this.changeReason = changeReason;
    }

    public Map<String, Object> getDiffSummary() {
        return diffSummary;
    }

    public void setDiffSummary(Map<String, Object> diffSummary) {
        this.diffSummary = diffSummary;
    }
}

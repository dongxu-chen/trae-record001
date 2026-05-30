package com.dtmonitor.diagnosis.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DiagnosisReport {

    private String xid;
    private Severity severity;
    private String rootCause;
    private String suggestion;
    private List<DiagnosisItem> items;
    private List<String> relatedTransactions;
    private RollbackLogAnalysis rollbackLog;

    public enum Severity {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DiagnosisItem {
        private String category;
        private String description;
        private String detail;
        private Severity severity;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RollbackLogAnalysis {
        private String triggerBranchId;
        private String triggerReason;
        private String cascadeDirection;
        private List<RollbackLogEntry> logChain;
        private String rootBranchId;
        private String rootErrorType;
        private String timelineSummary;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RollbackLogEntry {
        private int sequence;
        private String branchId;
        private String action;
        private String phase;
        private String errorMessage;
        private String eventTime;
        private boolean isRootCause;
    }
}

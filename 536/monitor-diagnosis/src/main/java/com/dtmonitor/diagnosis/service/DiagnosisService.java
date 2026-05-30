package com.dtmonitor.diagnosis.service;

import com.dtmonitor.core.enums.BranchStatus;
import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.core.service.BranchTransactionService;
import com.dtmonitor.core.service.GlobalTransactionService;
import com.dtmonitor.core.service.TransactionEventService;
import com.dtmonitor.diagnosis.model.DiagnosisReport;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
public class DiagnosisService {

    private final GlobalTransactionService globalTransactionService;
    private final BranchTransactionService branchTransactionService;
    private final TransactionEventService transactionEventService;
    private final RollbackLogAnalyzer rollbackLogAnalyzer;

    public DiagnosisService(GlobalTransactionService globalTransactionService,
                            BranchTransactionService branchTransactionService,
                            TransactionEventService transactionEventService,
                            RollbackLogAnalyzer rollbackLogAnalyzer) {
        this.globalTransactionService = globalTransactionService;
        this.branchTransactionService = branchTransactionService;
        this.transactionEventService = transactionEventService;
        this.rollbackLogAnalyzer = rollbackLogAnalyzer;
    }

    public DiagnosisReport diagnose(String xid) {
        GlobalTransaction tx = globalTransactionService.findById(xid);
        if (tx == null) {
            return DiagnosisReport.builder()
                    .xid(xid)
                    .severity(DiagnosisReport.Severity.LOW)
                    .rootCause("Transaction not found")
                    .build();
        }

        List<BranchTransaction> branches = branchTransactionService.findByXid(xid);
        List<TransactionEvent> events = transactionEventService.findByXid(xid);

        DiagnosisReport.DiagnosisReportBuilder reportBuilder = DiagnosisReport.builder()
                .xid(xid);

        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();

        items.addAll(diagnoseTimeout(tx));
        items.addAll(diagnoseRollback(tx, branches, events));
        items.addAll(diagnoseBranchFailures(branches));
        items.addAll(diagnoseModeSpecific(tx, branches));

        DiagnosisReport.RollbackLogAnalysis rollbackLog = null;
        if (tx.getStatus() == TransactionStatus.ROLLEDBACK
                || tx.getStatus() == TransactionStatus.ROLLBACKING
                || tx.getStatus() == TransactionStatus.FAILED) {
            rollbackLog = rollbackLogAnalyzer.analyze(tx, branches, events);
            if (rollbackLog != null) {
                items.addAll(analyzeRollbackLog(rollbackLog));
            }
        }

        DiagnosisReport.Severity severity = determineSeverity(items, tx);

        String rootCause = determineRootCause(items, tx, rollbackLog);
        String suggestion = generateSuggestion(items, tx);

        return reportBuilder
                .severity(severity)
                .rootCause(rootCause)
                .suggestion(suggestion)
                .items(items)
                .relatedTransactions(findRelatedTransactions(tx, branches))
                .rollbackLog(rollbackLog)
                .build();
    }

    private List<DiagnosisReport.DiagnosisItem> analyzeRollbackLog(DiagnosisReport.RollbackLogAnalysis analysis) {
        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();

        if (analysis.getRootBranchId() != null) {
            items.add(DiagnosisReport.DiagnosisItem.builder()
                    .category("ROLLBACK_ROOT")
                    .description(String.format("Root cause branch identified: %s", analysis.getRootBranchId()))
                    .detail(String.format("Error type: %s, Trigger: %s",
                            analysis.getRootErrorType(), analysis.getTriggerReason()))
                    .severity(DiagnosisReport.Severity.HIGH)
                    .build());
        }

        if (analysis.getLogChain() != null && analysis.getLogChain().size() > 1) {
            long rootCauseCount = analysis.getLogChain().stream()
                    .filter(DiagnosisReport.RollbackLogEntry::isRootCause).count();
            items.add(DiagnosisReport.DiagnosisItem.builder()
                    .category("ROLLBACK_CHAIN")
                    .description(String.format("Rollback cascade: %d events, %d root cause entries",
                            analysis.getLogChain().size(), rootCauseCount))
                    .detail(String.format("Direction: %s, %s",
                            analysis.getCascadeDirection(), analysis.getTimelineSummary()))
                    .severity(DiagnosisReport.Severity.MEDIUM)
                    .build());
        }

        if ("REVERSE_CASCADE".equals(analysis.getCascadeDirection())) {
            items.add(DiagnosisReport.DiagnosisItem.builder()
                    .category("ROLLBACK_REVERSE")
                    .description("Reverse cascade rollback detected - later branches rolled back before earlier ones")
                    .detail("This may indicate a compensation ordering issue in SAGA or TCC cancel phase")
                    .severity(DiagnosisReport.Severity.HIGH)
                    .build());
        }

        return items;
    }

    private List<DiagnosisReport.DiagnosisItem> diagnoseTimeout(GlobalTransaction tx) {
        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();
        if (tx.isTimeout()) {
            long duration = tx.getDurationMs();
            items.add(DiagnosisReport.DiagnosisItem.builder()
                    .category("TIMEOUT")
                    .description("Transaction exceeded timeout threshold")
                    .detail(String.format("Duration: %dms, Threshold: %dms", duration, tx.getTimeoutMs()))
                    .severity(DiagnosisReport.Severity.CRITICAL)
                    .build());
        }
        return items;
    }

    private List<DiagnosisReport.DiagnosisItem> diagnoseRollback(GlobalTransaction tx,
                                                                  List<BranchTransaction> branches,
                                                                  List<TransactionEvent> events) {
        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();

        if (tx.getStatus() == TransactionStatus.ROLLEDBACK || tx.getStatus() == TransactionStatus.ROLLBACKING) {
            String reason = tx.getRollbackReason();
            items.add(DiagnosisReport.DiagnosisItem.builder()
                    .category("ROLLBACK")
                    .description("Transaction was rolled back")
                    .detail(reason != null ? reason : "No specific rollback reason recorded")
                    .severity(DiagnosisReport.Severity.HIGH)
                    .build());

            List<BranchTransaction> failedBranches = branches.stream()
                    .filter(b -> b.getStatus() == BranchStatus.FAILED)
                    .collect(Collectors.toList());

            if (!failedBranches.isEmpty()) {
                for (BranchTransaction fb : failedBranches) {
                    items.add(DiagnosisReport.DiagnosisItem.builder()
                            .category("BRANCH_FAILURE")
                            .description(String.format("Branch %s failed", fb.getBranchId()))
                            .detail(fb.getErrorMessage() != null ? fb.getErrorMessage() : "Unknown error")
                            .severity(DiagnosisReport.Severity.HIGH)
                            .build());
                }
            }
        }
        return items;
    }

    private List<DiagnosisReport.DiagnosisItem> diagnoseBranchFailures(List<BranchTransaction> branches) {
        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();
        for (BranchTransaction branch : branches) {
            if (branch.getStatus() == BranchStatus.FAILED && branch.getErrorMessage() != null) {
                if (isConnectionError(branch.getErrorMessage())) {
                    items.add(DiagnosisReport.DiagnosisItem.builder()
                            .category("CONNECTION")
                            .description(String.format("Branch %s: Network/connection error detected", branch.getBranchId()))
                            .detail(branch.getErrorMessage())
                            .severity(DiagnosisReport.Severity.HIGH)
                            .build());
                } else if (isDeadlock(branch.getErrorMessage())) {
                    items.add(DiagnosisReport.DiagnosisItem.builder()
                            .category("DEADLOCK")
                            .description(String.format("Branch %s: Database deadlock detected", branch.getBranchId()))
                            .detail(branch.getErrorMessage())
                            .severity(DiagnosisReport.Severity.CRITICAL)
                            .build());
                }
            }
        }
        return items;
    }

    private List<DiagnosisReport.DiagnosisItem> diagnoseModeSpecific(GlobalTransaction tx,
                                                                      List<BranchTransaction> branches) {
        List<DiagnosisReport.DiagnosisItem> items = new ArrayList<>();

        if (tx.getMode() == TransactionMode.TCC) {
            long confirmCount = branches.stream()
                    .filter(b -> b.getStatus() == BranchStatus.PHASE_ONE_CONFIRM).count();
            long cancelCount = branches.stream()
                    .filter(b -> b.getStatus() == BranchStatus.PHASE_ONE_CANCEL).count();
            if (cancelCount > 0 && confirmCount == 0) {
                items.add(DiagnosisReport.DiagnosisItem.builder()
                        .category("TCC_CANCEL")
                        .description("TCC: All branches cancelled, no confirm executed")
                        .detail(String.format("Cancel count: %d, Confirm count: %d", cancelCount, confirmCount))
                        .severity(DiagnosisReport.Severity.HIGH)
                        .build());
            }
        }

        if (tx.getMode() == TransactionMode.SAGA) {
            long forwardCount = branches.stream()
                    .filter(b -> b.getStatus() == BranchStatus.PHASE_ONE_TRY).count();
            long compensateCount = branches.stream()
                    .filter(b -> b.getStatus() == BranchStatus.PHASE_ONE_CANCEL).count();
            if (compensateCount > forwardCount / 2) {
                items.add(DiagnosisReport.DiagnosisItem.builder()
                        .category("SAGA_COMPENSATION")
                        .description("SAGA: High compensation rate detected")
                        .detail(String.format("Forward: %d, Compensate: %d", forwardCount, compensateCount))
                        .severity(DiagnosisReport.Severity.MEDIUM)
                        .build());
            }
        }

        if (tx.getMode() == TransactionMode.AT) {
            List<BranchTransaction> lockedBranches = branches.stream()
                    .filter(b -> b.getLockKey() != null && !b.getLockKey().isEmpty())
                    .collect(Collectors.toList());
            if (lockedBranches.size() > 3) {
                items.add(DiagnosisReport.DiagnosisItem.builder()
                        .category("AT_LOCK_CONTENTION")
                        .description("AT: Potential lock contention with many locked branches")
                        .detail(String.format("Locked branches: %d / %d", lockedBranches.size(), branches.size()))
                        .severity(DiagnosisReport.Severity.MEDIUM)
                        .build());
            }
        }

        return items;
    }

    private DiagnosisReport.Severity determineSeverity(List<DiagnosisReport.DiagnosisItem> items,
                                                       GlobalTransaction tx) {
        if (items.stream().anyMatch(i -> i.getSeverity() == DiagnosisReport.Severity.CRITICAL)) {
            return DiagnosisReport.Severity.CRITICAL;
        }
        if (tx.getStatus() == TransactionStatus.FAILED || tx.getStatus() == TransactionStatus.TIMEOUT) {
            return DiagnosisReport.Severity.HIGH;
        }
        if (items.stream().anyMatch(i -> i.getSeverity() == DiagnosisReport.Severity.HIGH)) {
            return DiagnosisReport.Severity.HIGH;
        }
        if (!items.isEmpty()) {
            return DiagnosisReport.Severity.MEDIUM;
        }
        return DiagnosisReport.Severity.LOW;
    }

    private String determineRootCause(List<DiagnosisReport.DiagnosisItem> items,
                                       GlobalTransaction tx,
                                       DiagnosisReport.RollbackLogAnalysis rollbackLog) {
        if (rollbackLog != null && rollbackLog.getRootBranchId() != null) {
            return String.format("Root cause: branch %s (%s) - %s",
                    rollbackLog.getRootBranchId(),
                    rollbackLog.getRootErrorType(),
                    rollbackLog.getTriggerReason());
        }
        if (items.isEmpty()) {
            return tx.getStatus() == TransactionStatus.COMMITTED
                    ? "No issues detected" : "Status: " + tx.getStatus();
        }
        return items.stream()
                .filter(i -> i.getSeverity() == DiagnosisReport.Severity.CRITICAL
                        || i.getSeverity() == DiagnosisReport.Severity.HIGH)
                .findFirst()
                .map(DiagnosisReport.DiagnosisItem::getDescription)
                .orElse(items.get(0).getDescription());
    }

    private String generateSuggestion(List<DiagnosisReport.DiagnosisItem> items, GlobalTransaction tx) {
        StringBuilder sb = new StringBuilder();
        for (DiagnosisReport.DiagnosisItem item : items) {
            switch (item.getCategory()) {
                case "TIMEOUT":
                    sb.append("- Consider increasing transaction timeout or optimizing branch execution time.\n");
                    break;
                case "ROLLBACK":
                    sb.append("- Check branch failures and ensure compensating actions are idempotent.\n");
                    break;
                case "ROLLBACK_ROOT":
                    sb.append("- Focus on the identified root cause branch for targeted fix.\n");
                    break;
                case "ROLLBACK_CHAIN":
                    sb.append("- Review rollback cascade to prevent unnecessary compensations.\n");
                    break;
                case "ROLLBACK_REVERSE":
                    sb.append("- Investigate SAGA/TCC compensation ordering to avoid reverse cascades.\n");
                    break;
                case "BRANCH_FAILURE":
                    sb.append("- Inspect the failed branch service logs for detailed error information.\n");
                    break;
                case "CONNECTION":
                    sb.append("- Verify network connectivity between services and Seata Server.\n");
                    break;
                case "DEADLOCK":
                    sb.append("- Review database lock ordering and consider retry mechanisms.\n");
                    break;
                case "TCC_CANCEL":
                    sb.append("- Verify Try phase logic and ensure business pre-checks are correct.\n");
                    break;
                case "SAGA_COMPENSATION":
                    sb.append("- Review forward action reliability and reduce compensation triggers.\n");
                    break;
                case "AT_LOCK_CONTENTION":
                    sb.append("- Consider reducing lock scope or using optimistic locking strategy.\n");
                    break;
                default:
                    sb.append("- Review transaction configuration and service health.\n");
            }
        }
        return sb.toString();
    }

    private List<String> findRelatedTransactions(GlobalTransaction tx, List<BranchTransaction> branches) {
        return branches.stream()
                .map(BranchTransaction::getApplicationId)
                .filter(appId -> appId != null && !appId.equals(tx.getApplicationId()))
                .distinct()
                .collect(Collectors.toList());
    }

    private boolean isConnectionError(String message) {
        if (message == null) return false;
        String lower = message.toLowerCase();
        return lower.contains("connection") || lower.contains("timeout")
                || lower.contains("refused") || lower.contains("unreachable");
    }

    private boolean isDeadlock(String message) {
        if (message == null) return false;
        String lower = message.toLowerCase();
        return lower.contains("deadlock") || lower.contains("lock wait timeout");
    }
}

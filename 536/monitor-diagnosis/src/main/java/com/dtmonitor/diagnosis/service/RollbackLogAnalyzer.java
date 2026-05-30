package com.dtmonitor.diagnosis.service;

import com.dtmonitor.core.enums.BranchStatus;
import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.diagnosis.model.DiagnosisReport;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class RollbackLogAnalyzer {

    public DiagnosisReport.RollbackLogAnalysis analyze(GlobalTransaction tx,
                                                        List<BranchTransaction> branches,
                                                        List<TransactionEvent> events) {
        List<TransactionEvent> rollbackEvents = events.stream()
                .filter(e -> isRollbackRelated(e))
                .sorted(Comparator.comparing(TransactionEvent::getEventTime))
                .collect(Collectors.toList());

        if (rollbackEvents.isEmpty() && tx.getRollbackReason() == null) {
            return null;
        }

        String rootBranchId = identifyRootCauseBranch(branches, rollbackEvents);
        String rootErrorType = classifyRootError(tx, branches, rootBranchId);
        String triggerReason = determineTriggerReason(tx, rollbackEvents);
        String cascadeDirection = determineCascadeDirection(rollbackEvents);

        List<DiagnosisReport.RollbackLogEntry> logChain = buildLogChain(branches, rollbackEvents, rootBranchId);

        String timelineSummary = buildTimelineSummary(tx, rollbackEvents);

        return DiagnosisReport.RollbackLogAnalysis.builder()
                .triggerBranchId(findTriggerBranch(rollbackEvents, branches))
                .triggerReason(triggerReason)
                .cascadeDirection(cascadeDirection)
                .logChain(logChain)
                .rootBranchId(rootBranchId)
                .rootErrorType(rootErrorType)
                .timelineSummary(timelineSummary)
                .build();
    }

    private boolean isRollbackRelated(TransactionEvent event) {
        if (event.getEventType() == null) return false;
        String type = event.getEventType().toUpperCase();
        String phase = event.getPhase() != null ? event.getPhase().toUpperCase() : "";
        return type.contains("ROLLBACK") || type.contains("CANCEL")
                || phase.contains("ROLLBACK") || phase.contains("CANCEL")
                || (event.getErrorMessage() != null && !event.getErrorMessage().isEmpty());
    }

    private String identifyRootCauseBranch(List<BranchTransaction> branches,
                                            List<TransactionEvent> rollbackEvents) {
        Optional<TransactionEvent> firstError = rollbackEvents.stream()
                .filter(e -> e.getErrorMessage() != null && !e.getErrorMessage().isEmpty())
                .findFirst();

        if (firstError.isPresent() && firstError.get().getBranchId() != null) {
            return firstError.get().getBranchId();
        }

        return branches.stream()
                .filter(b -> b.getStatus() == BranchStatus.FAILED
                        || b.getStatus() == BranchStatus.PHASE_ONE_CANCEL)
                .map(BranchTransaction::getBranchId)
                .findFirst()
                .orElse(null);
    }

    private String classifyRootError(GlobalTransaction tx, List<BranchTransaction> branches,
                                      String rootBranchId) {
        if (rootBranchId == null) {
            if (tx.getRollbackReason() != null) {
                return classifyErrorMessage(tx.getRollbackReason());
            }
            return "UNKNOWN";
        }

        return branches.stream()
                .filter(b -> rootBranchId.equals(b.getBranchId()) && b.getErrorMessage() != null)
                .map(b -> classifyErrorMessage(b.getErrorMessage()))
                .findFirst()
                .orElse("UNKNOWN");
    }

    private String classifyErrorMessage(String message) {
        if (message == null) return "UNKNOWN";
        String lower = message.toLowerCase();
        if (lower.contains("deadlock") || lower.contains("lock wait timeout")) return "DEADLOCK";
        if (lower.contains("connection") || lower.contains("refused") || lower.contains("unreachable")) return "CONNECTION";
        if (lower.contains("timeout") || lower.contains("timed out")) return "TIMEOUT";
        if (lower.contains("null") || lower.contains("npe") || lower.contains("nullpointer")) return "NULL_POINTER";
        if (lower.contains("constraint") || lower.contains("duplicate") || lower.contains("unique")) return "DATA_CONSTRAINT";
        if (lower.contains("permission") || lower.contains("access") || lower.contains("forbidden")) return "PERMISSION";
        if (lower.contains("out of memory") || lower.contains("oom")) return "RESOURCE_EXHAUSTED";
        if (lower.contains("retry") || lower.contains("retries exhausted")) return "RETRY_EXHAUSTED";
        return "RUNTIME_ERROR";
    }

    private String determineTriggerReason(GlobalTransaction tx, List<TransactionEvent> rollbackEvents) {
        if (tx.getRollbackReason() != null && !tx.getRollbackReason().isEmpty()) {
            return tx.getRollbackReason();
        }
        if (!rollbackEvents.isEmpty()) {
            TransactionEvent first = rollbackEvents.get(0);
            return first.getErrorMessage() != null ? first.getErrorMessage() : first.getEventType();
        }
        return "No explicit rollback reason recorded";
    }

    private String determineCascadeDirection(List<TransactionEvent> rollbackEvents) {
        if (rollbackEvents.size() <= 1) return "SINGLE";
        Set<String> branchIds = rollbackEvents.stream()
                .map(TransactionEvent::getBranchId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        if (branchIds.size() == 1) return "SINGLE_BRANCH";
        TransactionEvent first = rollbackEvents.get(0);
        TransactionEvent last = rollbackEvents.get(rollbackEvents.size() - 1);
        if (first.getBranchId() != null && first.getBranchId().equals(last.getBranchId())) {
            return "RETRY_SAME_BRANCH";
        }
        boolean forward = true;
        for (int i = 1; i < rollbackEvents.size(); i++) {
            String prev = rollbackEvents.get(i - 1).getBranchId();
            String curr = rollbackEvents.get(i).getBranchId();
            if (prev != null && curr != null && prev.compareTo(curr) > 0) {
                forward = false;
                break;
            }
        }
        return forward ? "FORWARD_CASCADE" : "REVERSE_CASCADE";
    }

    private List<DiagnosisReport.RollbackLogEntry> buildLogChain(List<BranchTransaction> branches,
                                                                   List<TransactionEvent> rollbackEvents,
                                                                   String rootBranchId) {
        List<DiagnosisReport.RollbackLogEntry> chain = new ArrayList<>();
        int seq = 0;

        for (TransactionEvent event : rollbackEvents) {
            seq++;
            boolean isRoot = event.getBranchId() != null && event.getBranchId().equals(rootBranchId);
            chain.add(DiagnosisReport.RollbackLogEntry.builder()
                    .sequence(seq)
                    .branchId(event.getBranchId())
                    .action(event.getEventType())
                    .phase(event.getPhase())
                    .errorMessage(event.getErrorMessage())
                    .eventTime(event.getEventTime() != null ? event.getEventTime().toString() : null)
                    .isRootCause(isRoot)
                    .build());
        }

        for (BranchTransaction branch : branches) {
            if (branch.getStatus() == BranchStatus.FAILED
                    || branch.getStatus() == BranchStatus.PHASE_ONE_CANCEL) {
                boolean alreadyCovered = chain.stream()
                        .anyMatch(e -> branch.getBranchId().equals(e.getBranchId()));
                if (!alreadyCovered) {
                    seq++;
                    chain.add(DiagnosisReport.RollbackLogEntry.builder()
                            .sequence(seq)
                            .branchId(branch.getBranchId())
                            .action("BRANCH_" + branch.getStatus().name())
                            .phase("BRANCH_STATUS")
                            .errorMessage(branch.getErrorMessage())
                            .eventTime(branch.getBeginTime() != null ? branch.getBeginTime().toString() : null)
                            .isRootCause(branch.getBranchId().equals(rootBranchId))
                            .build());
                }
            }
        }

        return chain;
    }

    private String buildTimelineSummary(GlobalTransaction tx, List<TransactionEvent> rollbackEvents) {
        if (rollbackEvents.isEmpty()) {
            return "No rollback events found in transaction log.";
        }
        int totalEvents = rollbackEvents.size();
        long errorCount = rollbackEvents.stream()
                .filter(e -> e.getErrorMessage() != null && !e.getErrorMessage().isEmpty())
                .count();
        Set<String> affectedBranches = rollbackEvents.stream()
                .map(TransactionEvent::getBranchId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Rollback chain: %d events, %d errors, %d branches affected. ",
                totalEvents, errorCount, affectedBranches.size()));
        sb.append(String.format("Trigger: %s -> %s",
                rollbackEvents.get(0).getEventType(),
                rollbackEvents.get(rollbackEvents.size() - 1).getEventType()));
        return sb.toString();
    }

    private String findTriggerBranch(List<TransactionEvent> rollbackEvents,
                                      List<BranchTransaction> branches) {
        if (!rollbackEvents.isEmpty() && rollbackEvents.get(0).getBranchId() != null) {
            return rollbackEvents.get(0).getBranchId();
        }
        return branches.stream()
                .filter(b -> b.getStatus() == BranchStatus.FAILED)
                .map(BranchTransaction::getBranchId)
                .findFirst()
                .orElse(null);
    }
}

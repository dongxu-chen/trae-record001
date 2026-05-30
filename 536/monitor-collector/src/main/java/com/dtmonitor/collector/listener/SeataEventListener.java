package com.dtmonitor.collector.listener;

import com.dtmonitor.collector.event.SeataTransactionEvent;
import com.dtmonitor.core.enums.BranchStatus;
import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.core.service.BranchTransactionService;
import com.dtmonitor.core.service.GlobalTransactionService;
import com.dtmonitor.core.service.TransactionEventService;
import brave.Span;
import brave.Tracing;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Slf4j
@Component
@RequiredArgsConstructor
public class SeataEventListener {

    private final GlobalTransactionService globalTransactionService;
    private final BranchTransactionService branchTransactionService;
    private final TransactionEventService transactionEventService;
    private final Tracing tracing;

    @Async("collectorExecutor")
    @EventListener
    public void onTransactionEvent(SeataTransactionEvent event) {
        Span span = tracing.tracer().newTrace().name("process-transaction-event").start();
        span.tag("event.xid", event.getXid());
        span.tag("event.type", event.getEventType());

        MDC.put("xid", event.getXid());
        if (event.getTraceId() != null) {
            MDC.put("parentTraceId", event.getTraceId());
        }

        try {
            log.info("Received Seata transaction event: xid={}, branchId={}, type={}, status={}, traceId={}",
                    event.getXid(), event.getBranchId(), event.getEventType(), event.getStatus(), event.getTraceId());

            persistEvent(event);

            if (event.isGlobalEvent()) {
                handleGlobalTransaction(event);
            } else {
                handleBranchTransaction(event);
            }
        } catch (Exception e) {
            span.error(e);
            log.error("Error processing transaction event: xid={}", event.getXid(), e);
        } finally {
            span.finish();
            MDC.remove("xid");
            MDC.remove("parentTraceId");
        }
    }

    private void persistEvent(SeataTransactionEvent event) {
        TransactionEvent txEvent = TransactionEvent.builder()
                .xid(event.getXid())
                .branchId(event.getBranchId())
                .eventType(event.getEventType())
                .phase(determinePhase(event))
                .traceId(event.getTraceId())
                .spanId(event.getSpanId())
                .applicationId(event.getApplicationId())
                .payload(event.getPayload())
                .errorMessage(event.getErrorMessage())
                .eventTime(toLocalDateTime(event.getTimestamp()))
                .build();
        transactionEventService.save(txEvent);
    }

    private void handleGlobalTransaction(SeataTransactionEvent event) {
        GlobalTransaction existing = globalTransactionService.findById(event.getXid());

        if (existing == null) {
            GlobalTransaction tx = GlobalTransaction.builder()
                    .xid(event.getXid())
                    .applicationId(event.getApplicationId())
                    .transactionServiceGroup(event.getTransactionServiceGroup())
                    .mode(event.getMode() != null ? event.getMode() : TransactionMode.AT)
                    .status(event.getStatus() != null ? event.getStatus() : TransactionStatus.BEGIN)
                    .beginTime(toLocalDateTime(event.getTimestamp()))
                    .timeoutMs(event.getTimeoutMs())
                    .traceId(event.getTraceId())
                    .build();
            globalTransactionService.save(tx);
        } else {
            if (event.getStatus() != null) {
                globalTransactionService.updateStatus(event.getXid(), event.getStatus());
            }
            if (event.getTraceId() != null && existing.getTraceId() == null) {
                existing.setTraceId(event.getTraceId());
                globalTransactionService.save(existing);
            }
            if (event.getErrorMessage() != null) {
                existing.setRollbackReason(event.getErrorMessage());
                globalTransactionService.save(existing);
            }
        }
    }

    private void handleBranchTransaction(SeataTransactionEvent event) {
        BranchTransaction branch = BranchTransaction.builder()
                .branchId(event.getBranchId())
                .xid(event.getXid())
                .resourceId(event.getResourceId())
                .lockKey(event.getLockKey())
                .status(mapBranchStatus(event.getStatus()))
                .mode(event.getMode() != null ? event.getMode() : TransactionMode.AT)
                .applicationId(event.getApplicationId())
                .beginTime(toLocalDateTime(event.getTimestamp()))
                .traceId(event.getTraceId())
                .spanId(event.getSpanId())
                .errorMessage(event.getErrorMessage())
                .build();
        branchTransactionService.save(branch);
    }

    private BranchStatus mapBranchStatus(TransactionStatus status) {
        if (status == null) return BranchStatus.REGISTERED;
        switch (status) {
            case COMMITTED: return BranchStatus.PHASE_TWO_COMMIT;
            case ROLLEDBACK: return BranchStatus.PHASE_TWO_ROLLBACK;
            case ROLLBACKING: return BranchStatus.PHASE_ONE_CANCEL;
            case COMMITTING: return BranchStatus.PHASE_ONE_CONFIRM;
            case BEGIN: return BranchStatus.PHASE_ONE_TRY;
            case FAILED: return BranchStatus.FAILED;
            default: return BranchStatus.UNKNOWN;
        }
    }

    private String determinePhase(SeataTransactionEvent event) {
        if (event.getEventType() != null) {
            String type = event.getEventType().toUpperCase();
            if (type.contains("BEGIN") || type.contains("TRY")) return "PHASE_ONE";
            if (type.contains("COMMIT")) return "PHASE_TWO_COMMIT";
            if (type.contains("ROLLBACK") || type.contains("CANCEL")) return "PHASE_TWO_ROLLBACK";
        }
        return "UNKNOWN";
    }

    private LocalDateTime toLocalDateTime(Long timestamp) {
        if (timestamp == null) return LocalDateTime.now();
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(timestamp), ZoneId.systemDefault());
    }
}

package com.dtmonitor.collector.interceptor;

import com.dtmonitor.collector.event.SeataTransactionEvent;
import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import brave.Span;
import brave.Tracer;
import brave.Tracing;
import io.seata.core.event.Event;
import io.seata.core.event.GlobalTransactionEvent;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class SeataEventBridge {

    private final ApplicationEventPublisher eventPublisher;
    private final Tracing tracing;

    public SeataEventBridge(ApplicationEventPublisher eventPublisher, Tracing tracing) {
        this.eventPublisher = eventPublisher;
        this.tracing = tracing;
    }

    public void onSeataEvent(Event event) {
        if (event instanceof GlobalTransactionEvent) {
            GlobalTransactionEvent gte = (GlobalTransactionEvent) event;

            Tracer tracer = tracing.tracer();
            Span span = tracer.newTrace().name("seata-event-bridge").start();
            span.tag("seata.xid", gte.getId());
            span.tag("seata.event.type", gte.getType().name());

            MDC.put("xid", gte.getId());
            MDC.put("traceId", span.context().traceIdString());
            MDC.put("spanId", span.context().spanIdString());

            try {
                SeataTransactionEvent se = SeataTransactionEvent.builder()
                        .xid(gte.getId())
                        .eventType(gte.getType().name())
                        .mode(mapMode(gte.getMode()))
                        .status(mapStatus(gte.getStatus()))
                        .applicationId(gte.getApplicationId())
                        .transactionServiceGroup(gte.getGroup())
                        .timeoutMs(gte.getTimeout())
                        .traceId(span.context().traceIdString())
                        .spanId(String.valueOf(span.context().spanId()))
                        .timestamp(System.currentTimeMillis())
                        .build();
                eventPublisher.publishEvent(se);
                log.debug("Bridged Seata event: xid={}, type={}, traceId={}", gte.getId(), gte.getType(), se.getTraceId());
            } catch (Exception e) {
                span.error(e);
                throw e;
            } finally {
                span.finish();
                MDC.remove("xid");
                MDC.remove("traceId");
                MDC.remove("spanId");
            }
        }
    }

    private TransactionMode mapMode(String mode) {
        if (mode == null) return TransactionMode.AT;
        switch (mode.toUpperCase()) {
            case "TCC": return TransactionMode.TCC;
            case "SAGA": return TransactionMode.SAGA;
            case "XA": return TransactionMode.XA;
            default: return TransactionMode.AT;
        }
    }

    private TransactionStatus mapStatus(int statusCode) {
        switch (statusCode) {
            case 1: return TransactionStatus.BEGIN;
            case 2: return TransactionStatus.COMMITTING;
            case 3: return TransactionStatus.COMMITTED;
            case 4: return TransactionStatus.ROLLBACKING;
            case 5: return TransactionStatus.ROLLEDBACK;
            case 6: return TransactionStatus.TIMEOUT;
            default: return TransactionStatus.UNKNOWN;
        }
    }
}

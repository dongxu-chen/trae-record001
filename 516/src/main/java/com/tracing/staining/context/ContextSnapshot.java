package com.tracing.staining.context;

import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Data
@Builder
public class ContextSnapshot implements Serializable {

    private static final long serialVersionUID = 1L;

    private StainingContext stainingContext;
    private Map<String, String> mdcContext;
    private Context otelContext;
    private Map<TransmittableThreadLocal<Object>, Object> ttlContext;
    private long createTime;

    public static ContextSnapshot capture() {
        StainingContext stainingContext = TraceContextHolder.getContext();
        Map<String, String> mdcContext = MDC.getCopyOfContextMap();
        Context otelContext = Context.current();
        Map<TransmittableThreadLocal<Object>, Object> ttlContext = TransmittableThreadLocal.capture();

        ContextSnapshot snapshot = ContextSnapshot.builder()
                .stainingContext(stainingContext != null ? copyStainingContext(stainingContext) : null)
                .mdcContext(mdcContext != null ? new HashMap<>(mdcContext) : null)
                .otelContext(otelContext)
                .ttlContext(ttlContext)
                .createTime(System.currentTimeMillis())
                .build();

        log.debug("Context snapshot captured: traceId={}",
                stainingContext != null ? stainingContext.getTraceId() : "null");

        return snapshot;
    }

    public Scope setThreadContext() {
        Scope otelScope = null;

        try {
            Map<TransmittableThreadLocal<Object>, Object> ttlBackup =
                    TransmittableThreadLocal.backupAndSet(this.ttlContext);

            if (this.stainingContext != null) {
                StainingContext restoredContext = copyStainingContext(this.stainingContext);
                restoredContext.setSpanId(TraceContextHolder.generateSpanId());
                restoredContext.setTimestamp(System.currentTimeMillis());
                TraceContextHolder.setContext(restoredContext);
                log.debug("Staining context restored from snapshot: traceId={}",
                        restoredContext.getTraceId());
            }

            if (this.mdcContext != null) {
                MDC.setContextMap(this.mdcContext);
                log.debug("MDC context restored from snapshot");
            }

            if (this.otelContext != null) {
                otelScope = this.otelContext.makeCurrent();
                log.debug("OpenTelemetry context restored from snapshot");
            }

        } catch (Exception e) {
            log.error("Failed to restore context from snapshot", e);
        }

        return otelScope;
    }

    public void clearThreadContext(Scope otelScope) {
        try {
            if (otelScope != null) {
                try {
                    otelScope.close();
                } catch (Exception e) {
                    log.warn("Failed to close OpenTelemetry scope", e);
                }
            }
            MDC.clear();
            TraceContextHolder.removeContext();
            if (this.ttlContext != null) {
                TransmittableThreadLocal.restore(new HashMap<>());
            }
            log.debug("Thread context cleared after async execution");
        } catch (Exception e) {
            log.error("Failed to clear thread context", e);
        }
    }

    public static Runnable wrapWithSnapshot(Runnable task) {
        ContextSnapshot snapshot = capture();
        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();
                task.run();
            } finally {
                snapshot.clearThreadContext(otelScope);
            }
        };
    }

    public static <T> java.util.concurrent.Callable<T> wrapWithSnapshot(
            java.util.concurrent.Callable<T> task) {
        ContextSnapshot snapshot = capture();
        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();
                return task.call();
            } finally {
                snapshot.clearThreadContext(otelScope);
            }
        };
    }

    public Runnable applyToRunnable(Runnable task) {
        ContextSnapshot snapshot = this;
        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();
                task.run();
            } finally {
                snapshot.clearThreadContext(otelScope);
            }
        };
    }

    public <T> java.util.concurrent.Callable<T> applyToCallable(
            java.util.concurrent.Callable<T> task) {
        ContextSnapshot snapshot = this;
        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();
                return task.call();
            } finally {
                snapshot.clearThreadContext(otelScope);
            }
        };
    }

    private static StainingContext copyStainingContext(StainingContext source) {
        if (source == null) {
            return null;
        }
        return StainingContext.builder()
                .traceId(source.getTraceId())
                .spanId(source.getSpanId())
                .parentSpanId(source.getSpanId())
                .stainingFlag(source.getStainingFlag())
                .stainingColor(source.getStainingColor())
                .userId(source.getUserId())
                .bizType(source.getBizType())
                .sampled(source.getSampled())
                .requestId(source.getRequestId())
                .timestamp(source.getTimestamp())
                .extraAttributes(source.getExtraAttributes() != null
                        ? new HashMap<>(source.getExtraAttributes()) : null)
                .build();
    }

    public boolean isValid() {
        return stainingContext != null && stainingContext.getTraceId() != null;
    }
}

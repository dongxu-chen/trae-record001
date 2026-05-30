package com.tracing.staining.aspect;

import com.tracing.staining.context.ContextSnapshot;
import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import io.opentelemetry.context.Scope;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Slf4j
@Aspect
@Component
@Order(1)
public class TraceAsyncAspect {

    private static final ThreadLocal<ContextSnapshot> SNAPSHOT_HOLDER = new ThreadLocal<>();

    @Pointcut("@annotation(org.springframework.scheduling.annotation.Async)")
    public void asyncMethodPointcut() {
    }

    @Around("asyncMethodPointcut()")
    public Object aroundAsyncMethod(ProceedingJoinPoint joinPoint) throws Throwable {
        ContextSnapshot existingSnapshot = SNAPSHOT_HOLDER.get();
        boolean needsRestore = false;
        Scope otelScope = null;

        try {
            if (existingSnapshot != null && TraceContextHolder.getContext() == null) {
                otelScope = existingSnapshot.setThreadContext();

                if (existingSnapshot.isValid()) {
                    StainingContext asyncContext = TraceContextHolder.createChildContext();
                    TraceContextHolder.setContext(asyncContext);
                    TraceContextHolder.createAndSetOtelSpan(joinPoint.getSignature().toShortString());
                    log.debug("Async method restored from snapshot: traceId={}, spanId={}, method={}",
                            asyncContext.getTraceId(), asyncContext.getSpanId(),
                            joinPoint.getSignature().toShortString());
                    needsRestore = true;
                }
            } else if (TraceContextHolder.getContext() != null) {
                ContextSnapshot snapshot = ContextSnapshot.capture();
                SNAPSHOT_HOLDER.set(snapshot);
                log.debug("Captured snapshot for async method: traceId={}, method={}",
                        snapshot.getStainingContext() != null ? snapshot.getStainingContext().getTraceId() : "null",
                        joinPoint.getSignature().toShortString());
            }

            return joinPoint.proceed();

        } finally {
            if (needsRestore) {
                try {
                    TraceContextHolder.endOtelSpan();
                } finally {
                    if (existingSnapshot != null) {
                        existingSnapshot.clearThreadContext(otelScope);
                    }
                }
            }
        }
    }
}

package com.tracing.staining.async;

import com.tracing.staining.context.ContextSnapshot;
import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import io.opentelemetry.context.Scope;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Callable;
import java.util.concurrent.Future;

@Slf4j
public class TraceableThreadPoolTaskExecutor extends ThreadPoolTaskExecutor {

    @Override
    public void execute(Runnable task) {
        super.execute(wrapRunnable(task));
    }

    @Override
    public Future<?> submit(Runnable task) {
        return super.submit(wrapRunnable(task));
    }

    @Override
    public <T> Future<T> submit(Callable<T> task) {
        return super.submit(wrapCallable(task));
    }

    private Runnable wrapRunnable(Runnable task) {
        ContextSnapshot snapshot = ContextSnapshot.capture();
        log.debug("Captured context snapshot for async task: traceId={}",
                snapshot.getStainingContext() != null ? snapshot.getStainingContext().getTraceId() : "null");

        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();

                if (snapshot.isValid()) {
                    StainingContext asyncContext = TraceContextHolder.createChildContext();
                    TraceContextHolder.setContext(asyncContext);
                    TraceContextHolder.createAndSetOtelSpan("async-task");
                    log.debug("Async task started with restored context: traceId={}, spanId={}",
                            asyncContext.getTraceId(), asyncContext.getSpanId());
                }
                task.run();
            } finally {
                try {
                    TraceContextHolder.endOtelSpan();
                } finally {
                    snapshot.clearThreadContext(otelScope);
                }
            }
        };
    }

    private <T> Callable<T> wrapCallable(Callable<T> task) {
        ContextSnapshot snapshot = ContextSnapshot.capture();
        log.debug("Captured context snapshot for async callable: traceId={}",
                snapshot.getStainingContext() != null ? snapshot.getStainingContext().getTraceId() : "null");

        return () -> {
            Scope otelScope = null;
            try {
                otelScope = snapshot.setThreadContext();

                if (snapshot.isValid()) {
                    StainingContext asyncContext = TraceContextHolder.createChildContext();
                    TraceContextHolder.setContext(asyncContext);
                    TraceContextHolder.createAndSetOtelSpan("async-task");
                    log.debug("Async callable started with restored context: traceId={}, spanId={}",
                            asyncContext.getTraceId(), asyncContext.getSpanId());
                }
                return task.call();
            } finally {
                try {
                    TraceContextHolder.endOtelSpan();
                } finally {
                    snapshot.clearThreadContext(otelScope);
                }
            }
        };
    }
}

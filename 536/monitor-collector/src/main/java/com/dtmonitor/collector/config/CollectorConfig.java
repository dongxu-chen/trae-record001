package com.dtmonitor.collector.config;

import brave.Tracing;
import org.slf4j.MDC;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.TaskDecorator;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.Map;
import java.util.concurrent.Executor;

@Configuration
@EnableAsync
public class CollectorConfig {

    @Bean("collectorExecutor")
    public Executor collectorExecutor(Tracing tracing) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(4);
        executor.setMaxPoolSize(16);
        executor.setQueueCapacity(1024);
        executor.setThreadNamePrefix("collector-");
        executor.setRejectedExecutionHandler((r, e) -> {
            throw new RuntimeException("Collector queue full, event rejected");
        });
        executor.setTaskDecorator(new TraceContextTaskDecorator(tracing));
        executor.initialize();
        return executor;
    }

    public static class TraceContextTaskDecorator implements TaskDecorator {

        private final Tracing tracing;

        public TraceContextTaskDecorator(Tracing tracing) {
            this.tracing = tracing;
        }

        @Override
        public Runnable decorate(Runnable runnable) {
            Map<String, String> contextMap = MDC.getCopyOfContextMap();
            brave.Span currentSpan = tracing.tracer().currentSpan();
            brave.propagation.TraceContext traceContext = currentSpan != null ? currentSpan.context() : null;

            return () -> {
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                }
                brave.Span childSpan = null;
                if (traceContext != null) {
                    childSpan = tracing.tracer().newChild(traceContext);
                    childSpan.name("async-collector").start();
                    MDC.put("traceId", childSpan.context().traceIdString());
                    MDC.put("spanId", childSpan.context().spanIdString());
                }
                try {
                    runnable.run();
                } finally {
                    if (childSpan != null) {
                        childSpan.finish();
                    }
                    MDC.clear();
                }
            };
        }
    }
}

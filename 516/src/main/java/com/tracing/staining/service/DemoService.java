package com.tracing.staining.service;

import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.sampler.AdaptiveTraceSampler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

@Slf4j
@Service
@RequiredArgsConstructor
public class DemoService {

    private final RestTemplate restTemplate;
    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final Executor traceAsyncExecutor;
    private final AdaptiveTraceSampler adaptiveTraceSampler;

    public Map<String, Object> getCurrentTraceContext() {
        StainingContext context = TraceContextHolder.getContext();
        Map<String, Object> result = new HashMap<>();
        if (context != null) {
            result.put("traceId", context.getTraceId());
            result.put("spanId", context.getSpanId());
            result.put("parentSpanId", context.getParentSpanId());
            result.put("stainingFlag", context.getStainingFlag());
            result.put("stainingColor", context.getStainingColor());
            result.put("userId", context.getUserId());
            result.put("bizType", context.getBizType());
            result.put("sampled", context.getSampled());
            result.put("requestId", context.getRequestId());
            result.put("timestamp", context.getTimestamp());
            result.put("extraAttributes", context.getExtraAttributes());
        } else {
            result.put("message", "No trace context found");
        }
        return result;
    }

    @Async("traceAsyncExecutor")
    public CompletableFuture<Map<String, Object>> asyncMethodDemo() {
        log.info("Executing async method with trace context");
        Map<String, Object> result = getCurrentTraceContext();
        result.put("method", "asyncMethodDemo");
        result.put("thread", Thread.currentThread().getName());
        return CompletableFuture.completedFuture(result);
    }

    public CompletableFuture<Map<String, Object>> threadPoolDemo() {
        CompletableFuture<Map<String, Object>> future = new CompletableFuture<>();
        traceAsyncExecutor.execute(() -> {
            log.info("Executing in thread pool with trace context");
            Map<String, Object> result = getCurrentTraceContext();
            result.put("method", "threadPoolDemo");
            result.put("thread", Thread.currentThread().getName());
            future.complete(result);
        });
        return future;
    }

    public Map<String, Object> restTemplateDemo(String url) {
        log.info("Calling downstream service: {}", url);
        Map<String, Object> result = new HashMap<>();
        try {
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);
            result.put("downstreamResponse", response);
            result.put("currentContext", getCurrentTraceContext());
        } catch (Exception e) {
            log.error("Failed to call downstream service", e);
            result.put("error", e.getMessage());
        }
        return result;
    }

    public Map<String, Object> sendKafkaMessage(String topic, Object message) {
        log.info("Sending Kafka message to topic: {}", topic);
        Map<String, Object> result = new HashMap<>();
        try {
            kafkaTemplate.send(topic, message);
            result.put("status", "success");
            result.put("topic", topic);
            result.put("currentContext", getCurrentTraceContext());
        } catch (Exception e) {
            log.error("Failed to send Kafka message", e);
            result.put("status", "error");
            result.put("error", e.getMessage());
        }
        return result;
    }

    public Map<String, Object> sendRabbitMessage(String exchange, String routingKey, Object message) {
        log.info("Sending RabbitMQ message to exchange: {}, routingKey: {}", exchange, routingKey);
        Map<String, Object> result = new HashMap<>();
        try {
            rabbitTemplate.convertAndSend(exchange, routingKey, message);
            result.put("status", "success");
            result.put("exchange", exchange);
            result.put("routingKey", routingKey);
            result.put("currentContext", getCurrentTraceContext());
        } catch (Exception e) {
            log.error("Failed to send RabbitMQ message", e);
            result.put("status", "error");
            result.put("error", e.getMessage());
        }
        return result;
    }

    public Map<String, Object> nestedCallDemo() {
        log.info("Starting nested call demo");

        Map<String, Object> result = new HashMap<>();
        result.put("level1", getCurrentTraceContext());

        StainingContext childContext = TraceContextHolder.createChildContext();
        TraceContextHolder.setContext(childContext);
        try {
            log.info("Executing level 2 nested call");
            result.put("level2", getCurrentTraceContext());

            StainingContext grandChildContext = TraceContextHolder.createChildContext();
            TraceContextHolder.setContext(grandChildContext);
            try {
                log.info("Executing level 3 nested call");
                result.put("level3", getCurrentTraceContext());
            } finally {
                TraceContextHolder.removeContext();
            }
        } finally {
            TraceContextHolder.removeContext();
        }

        return result;
    }

    public Map<String, Object> manualStainingDemo(boolean stainingFlag, String stainingColor,
                                                  String userId, String bizType) {
        log.info("Manual staining demo: flag={}, color={}, userId={}, bizType={}",
                stainingFlag, stainingColor, userId, bizType);

        StainingContext context = TraceContextHolder.createNewContext(
                stainingFlag, stainingColor, userId, bizType);
        TraceContextHolder.setContext(context);
        TraceContextHolder.createAndSetOtelSpan("manual-staining-demo");

        try {
            Map<String, Object> result = getCurrentTraceContext();
            result.put("method", "manualStainingDemo");
            return result;
        } finally {
            TraceContextHolder.endOtelSpan();
            TraceContextHolder.removeContext();
        }
    }

    public boolean isCurrentRequestStained() {
        return TraceContextHolder.isStainingEnabled();
    }

    public Map<String, Object> getSamplerStatus() {
        AdaptiveTraceSampler.SamplerStatus status = adaptiveTraceSampler.getStatus();
        Map<String, Object> result = new HashMap<>();

        result.put("currentSampleRate", String.format("%.4f", status.getCurrentSampleRate()));
        result.put("currentStainingRate", String.format("%.4f", status.getCurrentStainingRate()));
        result.put("currentQps", status.getCurrentQps());
        result.put("currentConcurrency", status.getCurrentConcurrency());
        result.put("baseSampleRate", status.getBaseSampleRate());
        result.put("minSampleRate", status.getMinSampleRate());
        result.put("maxSampleRate", status.getMaxSampleRate());
        result.put("qpsHighThreshold", status.getQpsHighThreshold());
        result.put("qpsLowThreshold", status.getQpsLowThreshold());
        result.put("concurrencyHighThreshold", status.getConcurrencyHighThreshold());
        result.put("concurrencyLowThreshold", status.getConcurrencyLowThreshold());

        String loadStatus;
        if (status.getCurrentQps() > status.getQpsHighThreshold()
                || status.getCurrentConcurrency() > status.getConcurrencyHighThreshold()) {
            loadStatus = "HIGH_LOAD - Sample rate reduced";
        } else if (status.getCurrentQps() < status.getQpsLowThreshold()
                && status.getCurrentConcurrency() < status.getConcurrencyLowThreshold()) {
            loadStatus = "LOW_LOAD - Sample rate increased";
        } else {
            loadStatus = "NORMAL_LOAD - Sample rate at base";
        }
        result.put("loadStatus", loadStatus);

        log.info("Sampler status requested: qps={}, concurrency={}, sampleRate={}, status={}",
                status.getCurrentQps(), status.getCurrentConcurrency(),
                String.format("%.4f", status.getCurrentSampleRate()), loadStatus);

        return result;
    }
}

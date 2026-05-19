package com.pushplatform.push.reactive;

import io.micrometer.core.instrument.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class PushMonitorService {

    private static final Logger logger = LoggerFactory.getLogger(PushMonitorService.class);

    private final MeterRegistry meterRegistry;
    private final Map<String, Timer> channelTimers = new ConcurrentHashMap<>();
    private final Map<String, Counter> successCounters = new ConcurrentHashMap<>();
    private final Map<String, Counter> failureCounters = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> slidingWindowLatency = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> slidingWindowCount = new ConcurrentHashMap<>();

    private volatile int dynamicConcurrencyFactor = 100;

    public PushMonitorService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    @PostConstruct
    public void init() {
        initChannelMetrics("fcm");
        initChannelMetrics("apns");
        initChannelMetrics("websocket");

        startDynamicAdjustmentTask();

        logger.info("PushMonitorService initialized");
    }

    private void initChannelMetrics(String channel) {
        channelTimers.put(channel, Timer.builder("push.latency")
                .tag("channel", channel)
                .description("Push request latency")
                .register(meterRegistry));

        successCounters.put(channel, Counter.builder("push.success")
                .tag("channel", channel)
                .description("Successful push count")
                .register(meterRegistry));

        failureCounters.put(channel, Counter.builder("push.failure")
                .tag("channel", channel)
                .description("Failed push count")
                .register(meterRegistry));

        Gauge.builder("push.success.rate", this, s -> calculateSuccessRate(channel))
                .tag("channel", channel)
                .description("Push success rate")
                .register(meterRegistry);

        slidingWindowLatency.put(channel, new AtomicLong(0));
        slidingWindowCount.put(channel, new AtomicLong(0));
    }

    public <T> Mono<T> monitor(String channel, Mono<T> mono) {
        long startTime = System.nanoTime();
        return mono.doOnSuccess(result -> {
                    recordSuccess(channel, System.nanoTime() - startTime);
                })
                .doOnError(error -> {
                    recordFailure(channel, System.nanoTime() - startTime);
                });
    }

    private void recordSuccess(String channel, long latencyNanos) {
        Timer timer = channelTimers.get(channel);
        if (timer != null) {
            timer.record(Duration.ofNanos(latencyNanos));
        }
        Counter counter = successCounters.get(channel);
        if (counter != null) {
            counter.increment();
        }
        updateSlidingWindow(channel, latencyNanos, true);
    }

    private void recordFailure(String channel, long latencyNanos) {
        Timer timer = channelTimers.get(channel);
        if (timer != null) {
            timer.record(Duration.ofNanos(latencyNanos));
        }
        Counter counter = failureCounters.get(channel);
        if (counter != null) {
            counter.increment();
        }
        updateSlidingWindow(channel, latencyNanos, false);
    }

    private void updateSlidingWindow(String channel, long latencyNanos, boolean success) {
        AtomicLong totalLatency = slidingWindowLatency.get(channel);
        AtomicLong count = slidingWindowCount.get(channel);

        if (totalLatency != null && count != null) {
            totalLatency.addAndGet(latencyNanos);
            count.incrementAndGet();
        }
    }

    private double calculateSuccessRate(String channel) {
        Counter success = successCounters.get(channel);
        Counter failure = failureCounters.get(channel);

        if (success == null || failure == null) {
            return 100.0;
        }

        double total = success.count() + failure.count();
        if (total == 0) {
            return 100.0;
        }
        return (success.count() / total) * 100;
    }

    public double getAverageLatencyMs(String channel) {
        Timer timer = channelTimers.get(channel);
        if (timer == null) {
            return 0.0;
        }
        return timer.mean(TimeUnit.MILLISECONDS);
    }

    public double getP95LatencyMs(String channel) {
        Timer timer = channelTimers.get(channel);
        if (timer == null) {
            return 0.0;
        }
        return timer.takeSnapshot().percentileValues()[1].value(TimeUnit.MILLISECONDS);
    }

    private void startDynamicAdjustmentTask() {
        reactor.core.publisher.Flux.interval(Duration.ofSeconds(30))
                .doOnNext(tick -> performDynamicAdjustment())
                .onErrorContinue((e, obj) -> logger.error("Dynamic adjustment task error", e))
                .subscribe();
    }

    private void performDynamicAdjustment() {
        for (String channel : channelTimers.keySet()) {
            double avgLatency = getAverageLatencyMs(channel);
            double successRate = calculateSuccessRate(channel);

            if (avgLatency > 500 || successRate < 90) {
                reduceConcurrency(channel);
            } else if (avgLatency < 100 && successRate > 98) {
                increaseConcurrency(channel);
            }
        }
    }

    private void reduceConcurrency(String channel) {
        if (dynamicConcurrencyFactor > 30) {
            dynamicConcurrencyFactor = Math.max(30, dynamicConcurrencyFactor - 10);
            logger.info("Reducing concurrency for {}: factor={}", channel, dynamicConcurrencyFactor);
        }
    }

    private void increaseConcurrency(String channel) {
        if (dynamicConcurrencyFactor < 150) {
            dynamicConcurrencyFactor = Math.min(150, dynamicConcurrencyFactor + 5);
            logger.info("Increasing concurrency for {}: factor={}", channel, dynamicConcurrencyFactor);
        }
    }

    public int getDynamicConcurrencyFactor() {
        return dynamicConcurrencyFactor;
    }

    public Map<String, Object> getChannelStats(String channel) {
        Map<String, Object> stats = new ConcurrentHashMap<>();
        stats.put("successRate", calculateSuccessRate(channel));
        stats.put("avgLatencyMs", getAverageLatencyMs(channel));
        stats.put("p95LatencyMs", getP95LatencyMs(channel));
        stats.put("concurrencyFactor", dynamicConcurrencyFactor);
        return stats;
    }
}

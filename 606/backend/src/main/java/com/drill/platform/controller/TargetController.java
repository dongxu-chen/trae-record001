package com.drill.platform.controller;

import com.alibaba.csp.sentinel.Entry;
import com.alibaba.csp.sentinel.SphU;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.drill.platform.sentinel.SentinelManager;
import com.drill.platform.sentinel.SentinelMetric;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicLong;

@RestController
@RequestMapping("/api/drill")
@Slf4j
public class TargetController {

    private final SentinelManager sentinelManager;
    private final Map<String, AtomicLong> requestCounters = new ConcurrentHashMap<>();
    private volatile boolean chaosEnabled = false;
    private volatile double chaosRatio = 0.0;
    private volatile long artificialDelayMs = 0;

    public TargetController(SentinelManager sentinelManager) {
        this.sentinelManager = sentinelManager;
    }

    @GetMapping("/target")
    public Map<String, Object> targetEndpoint(
            @RequestParam(defaultValue = "default") String strategyId) {
        long start = System.currentTimeMillis();

        SentinelMetric metric = sentinelManager.getMetric(strategyId);
        if (metric != null) {
            metric.incrementPassed();
        }

        if (chaosEnabled && ThreadLocalRandom.current().nextDouble() < chaosRatio) {
            throw new RuntimeException("Chaos injected error");
        }

        if (artificialDelayMs > 0) {
            try {
                Thread.sleep(artificialDelayMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        requestCounters.computeIfAbsent(strategyId, k -> new AtomicLong(0)).incrementAndGet();

        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "OK");
        response.put("timestamp", System.currentTimeMillis());
        response.put("responseTime", System.currentTimeMillis() - start);
        return response;
    }

    @PostMapping("/chaos")
    public Map<String, Object> configureChaos(
            @RequestParam(defaultValue = "false") boolean enabled,
            @RequestParam(defaultValue = "0.0") double errorRatio,
            @RequestParam(defaultValue = "0") long delayMs) {
        this.chaosEnabled = enabled;
        this.chaosRatio = errorRatio;
        this.artificialDelayMs = delayMs;

        Map<String, Object> response = new HashMap<>();
        response.put("chaosEnabled", chaosEnabled);
        response.put("chaosRatio", chaosRatio);
        response.put("artificialDelayMs", artificialDelayMs);
        return response;
    }

    @GetMapping("/metrics")
    public Map<String, Object> getMetrics(@RequestParam(defaultValue = "default") String strategyId) {
        SentinelMetric metric = sentinelManager.getMetric(strategyId);
        Map<String, Object> response = new HashMap<>();
        if (metric != null) {
            response.put("passedCount", metric.getPassedCount());
            response.put("blockedCount", metric.getBlockedCount());
            response.put("degradedCount", metric.getDegradedCount());
            response.put("blockRate", metric.getBlockRate());
            response.put("passRate", metric.getPassRate());
        }
        response.put("requestCount", requestCounters.getOrDefault(strategyId, new AtomicLong(0)).get());
        return response;
    }
}

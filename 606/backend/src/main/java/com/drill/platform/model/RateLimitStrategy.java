package com.drill.platform.model;

import lombok.Data;

@Data
public class RateLimitStrategy {

    private String id;
    private String name;
    private String description;
    private StrategyType type;
    private int threshold;
    private int timeoutMs;
    private String fallbackResponse;
    private double circuitBreakerRatio;
    private int circuitBreakerTimeoutMs;
    private int warmupPeriodSec;
    private int maxQueueingTimeMs;
    private boolean enabled;

    public enum StrategyType {
        DIRECT_REJECT,
        WARM_UP,
        RATE_LIMITER,
        CIRCUIT_BREAKER,
        ADAPTIVE
    }

    public static RateLimitStrategy defaultStrategy() {
        RateLimitStrategy strategy = new RateLimitStrategy();
        strategy.setName("Default Strategy");
        strategy.setType(StrategyType.DIRECT_REJECT);
        strategy.setThreshold(50);
        strategy.setTimeoutMs(5000);
        strategy.setFallbackResponse("{\"code\":429,\"message\":\"Rate limited\"}");
        strategy.setCircuitBreakerRatio(0.5);
        strategy.setCircuitBreakerTimeoutMs(10000);
        strategy.setWarmupPeriodSec(10);
        strategy.setMaxQueueingTimeMs(500);
        strategy.setEnabled(true);
        return strategy;
    }
}

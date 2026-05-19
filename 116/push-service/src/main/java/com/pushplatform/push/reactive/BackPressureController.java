package com.pushplatform.push.reactive;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.reactor.circuitbreaker.operator.CircuitBreakerOperator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class BackPressureController {

    private static final Logger logger = LoggerFactory.getLogger(BackPressureController.class);

    private final CircuitBreakerRegistry circuitBreakerRegistry;
    private final Map<String, CircuitBreaker> channelCircuitBreakers = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> channelInflightRequests = new ConcurrentHashMap<>();
    private final Map<String, AtomicInteger> channelConcurrencyLimits = new ConcurrentHashMap<>();

    public BackPressureController() {
        this.circuitBreakerRegistry = CircuitBreakerRegistry.ofDefaults();
    }

    @PostConstruct
    public void init() {
        initChannel("fcm", 100, 50);
        initChannel("apns", 80, 40);
        initChannel("websocket", 200, 100);
        logger.info("BackPressureController initialized with channel circuit breakers");
    }

    private void initChannel(String channel, int concurrencyLimit, int slidingWindowSize) {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .failureRateThreshold(50)
                .waitDurationInOpenState(Duration.ofSeconds(30))
                .permittedNumberOfCallsInHalfOpenState(10)
                .slidingWindowSize(slidingWindowSize)
                .minimumNumberOfCalls(20)
                .build();

        CircuitBreaker circuitBreaker = circuitBreakerRegistry.circuitBreaker(channel, config);
        channelCircuitBreakers.put(channel, circuitBreaker);
        channelInflightRequests.put(channel, new AtomicLong(0));
        channelConcurrencyLimits.put(channel, new AtomicInteger(concurrencyLimit));

        circuitBreaker.getEventPublisher()
                .onStateTransition(event -> {
                    logger.warn("Circuit breaker {} state changed: {} -> {}",
                            channel, event.getStateTransition().getFromState(),
                            event.getStateTransition().getToState());
                })
                .onFailureRateExceeded(event -> {
                    logger.error("Circuit breaker {} failure rate exceeded: {}%",
                            channel, event.getFailureRate());
                });
    }

    public <T> Mono<T> applyBackPressure(String channel, Mono<T> mono) {
        CircuitBreaker circuitBreaker = channelCircuitBreakers.get(channel);
        if (circuitBreaker == null) {
            return mono;
        }

        return checkConcurrencyLimit(channel)
                .flatMap(canProceed -> {
                    if (!canProceed) {
                        return Mono.error(new BackPressureException("Concurrency limit exceeded for channel: " + channel));
                    }
                    return mono.transformDeferred(CircuitBreakerOperator.of(circuitBreaker))
                            .doOnSuccess(success -> decrementInflight(channel))
                            .doOnError(error -> decrementInflight(channel));
                });
    }

    private Mono<Boolean> checkConcurrencyLimit(String channel) {
        AtomicLong inflight = channelInflightRequests.get(channel);
        AtomicInteger limit = channelConcurrencyLimits.get(channel);

        if (inflight == null || limit == null) {
            return Mono.just(true);
        }

        long current = inflight.incrementAndGet();
        if (current > limit.get()) {
            inflight.decrementAndGet();
            logger.warn("Concurrency limit reached for {}: {}/{}", channel, current, limit.get());
            return Mono.just(false);
        }

        return Mono.just(true);
    }

    private void decrementInflight(String channel) {
        AtomicLong inflight = channelInflightRequests.get(channel);
        if (inflight != null) {
            inflight.decrementAndGet();
        }
    }

    public void updateConcurrencyLimit(String channel, int newLimit) {
        AtomicInteger limit = channelConcurrencyLimits.get(channel);
        if (limit != null) {
            int oldLimit = limit.getAndSet(newLimit);
            logger.info("Updated concurrency limit for {}: {} -> {}", channel, oldLimit, newLimit);
        }
    }

    public long getInflightRequests(String channel) {
        AtomicLong inflight = channelInflightRequests.get(channel);
        return inflight != null ? inflight.get() : 0;
    }

    public CircuitBreaker.State getCircuitBreakerState(String channel) {
        CircuitBreaker cb = channelCircuitBreakers.get(channel);
        return cb != null ? cb.getState() : CircuitBreaker.State.CLOSED;
    }

    public static class BackPressureException extends RuntimeException {
        public BackPressureException(String message) {
            super(message);
        }
    }
}

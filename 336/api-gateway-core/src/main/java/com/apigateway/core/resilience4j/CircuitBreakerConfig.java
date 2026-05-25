package com.apigateway.core.resilience4j;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.circuitbreaker.event.CircuitBreakerOnStateTransitionEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 断路器配置类
 * 配置多个断路器实例，为不同服务提供熔断保护
 * 半开状态采用单请求探测，成功后逐步增大流量
 * 包含滑动窗口、失败率阈值、慢调用阈值、等待时间等配置
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Configuration
public class CircuitBreakerConfig {

    /**
     * 半开状态流量递增因子
     * 每次成功探测后，允许的请求数乘以该因子
     */
    private static final int HALF_OPEN_SCALE_FACTOR = 2;

    /**
     * 半开状态最大允许请求数
     */
    private static final int MAX_HALF_OPEN_CALLS = 50;

    /**
     * 各断路器半开状态已成功探测次数
     */
    private final ConcurrentHashMap<String, AtomicInteger> successfulProbes = new ConcurrentHashMap<>();

    /**
     * REST服务断路器
     * 配置滑动窗口大小为100，失败率阈值50%，慢调用阈值60%
     * 熔断等待时间为30秒，半开状态允许1个请求探测
     *
     * @param registry 断路器注册中心
     * @return REST服务断路器实例
     */
    @Bean
    public CircuitBreaker restServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                .failureRateThreshold(50)
                .slowCallRateThreshold(60)
                .slowCallDurationThreshold(Duration.ofMillis(500))
                .permittedNumberOfCallsInHalfOpenState(1)
                .maxWaitDurationInHalfOpenState(Duration.ofSeconds(10))
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(100)
                .minimumNumberOfCalls(20)
                .waitDurationInOpenState(Duration.ofSeconds(30))
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        CircuitBreaker circuitBreaker = registry.circuitBreaker("restService", config);
        registerStateTransitionListener(circuitBreaker);
        return circuitBreaker;
    }

    /**
     * gRPC服务断路器
     * 配置滑动窗口大小为150，失败率阈值40%，慢调用阈值70%
     * 熔断等待时间为45秒，半开状态允许1个请求探测
     *
     * @param registry 断路器注册中心
     * @return gRPC服务断路器实例
     */
    @Bean
    public CircuitBreaker grpcServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                .failureRateThreshold(40)
                .slowCallRateThreshold(70)
                .slowCallDurationThreshold(Duration.ofMillis(800))
                .permittedNumberOfCallsInHalfOpenState(1)
                .maxWaitDurationInHalfOpenState(Duration.ofSeconds(15))
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(150)
                .minimumNumberOfCalls(30)
                .waitDurationInOpenState(Duration.ofSeconds(45))
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        CircuitBreaker circuitBreaker = registry.circuitBreaker("grpcService", config);
        registerStateTransitionListener(circuitBreaker);
        return circuitBreaker;
    }

    /**
     * GraphQL服务断路器
     * 配置滑动窗口大小为80，失败率阈值60%，慢调用阈值50%
     * 熔断等待时间为20秒，半开状态允许1个请求探测
     *
     * @param registry 断路器注册中心
     * @return GraphQL服务断路器实例
     */
    @Bean
    public CircuitBreaker graphqlServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                .failureRateThreshold(60)
                .slowCallRateThreshold(50)
                .slowCallDurationThreshold(Duration.ofMillis(1000))
                .permittedNumberOfCallsInHalfOpenState(1)
                .maxWaitDurationInHalfOpenState(Duration.ofSeconds(8))
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(80)
                .minimumNumberOfCalls(15)
                .waitDurationInOpenState(Duration.ofSeconds(20))
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        CircuitBreaker circuitBreaker = registry.circuitBreaker("graphqlService", config);
        registerStateTransitionListener(circuitBreaker);
        return circuitBreaker;
    }

    /**
     * 聚合服务断路器
     * 配置滑动窗口大小为200，失败率阈值30%，慢调用阈值80%
     * 熔断等待时间为60秒，半开状态允许1个请求探测
     *
     * @param registry 断路器注册中心
     * @return 聚合服务断路器实例
     */
    @Bean
    public CircuitBreaker aggregateServiceCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                .failureRateThreshold(30)
                .slowCallRateThreshold(80)
                .slowCallDurationThreshold(Duration.ofMillis(2000))
                .permittedNumberOfCallsInHalfOpenState(1)
                .maxWaitDurationInHalfOpenState(Duration.ofSeconds(20))
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(200)
                .minimumNumberOfCalls(50)
                .waitDurationInOpenState(Duration.ofSeconds(60))
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        CircuitBreaker circuitBreaker = registry.circuitBreaker("aggregateService", config);
        registerStateTransitionListener(circuitBreaker);
        return circuitBreaker;
    }

    /**
     * 默认断路器
     * 配置滑动窗口大小为300，失败率阈值50%，慢调用阈值70%
     * 熔断等待时间为30秒，半开状态允许1个请求探测
     * 用于未匹配到特定服务的通用熔断保护
     *
     * @param registry 断路器注册中心
     * @return 默认断路器实例
     */
    @Bean
    public CircuitBreaker defaultCircuitBreaker(CircuitBreakerRegistry registry) {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                .failureRateThreshold(50)
                .slowCallRateThreshold(70)
                .slowCallDurationThreshold(Duration.ofMillis(1500))
                .permittedNumberOfCallsInHalfOpenState(1)
                .maxWaitDurationInHalfOpenState(Duration.ofSeconds(10))
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(300)
                .minimumNumberOfCalls(50)
                .waitDurationInOpenState(Duration.ofSeconds(30))
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        CircuitBreaker circuitBreaker = registry.circuitBreaker("default", config);
        registerStateTransitionListener(circuitBreaker);
        return circuitBreaker;
    }

    /**
     * 注册断路器状态转换监听器
     * 实现半开状态单请求探测，成功后逐步增大流量的逻辑
     *
     * @param circuitBreaker 断路器实例
     */
    private void registerStateTransitionListener(CircuitBreaker circuitBreaker) {
        String circuitBreakerName = circuitBreaker.getName();

        circuitBreaker.getEventPublisher()
                .onStateTransition(event -> handleStateTransition(event, circuitBreakerName))
                .onSuccess(event -> handleSuccess(event, circuitBreakerName, circuitBreaker))
                .onError(event -> handleError(event, circuitBreakerName, circuitBreaker));

        successfulProbes.put(circuitBreakerName, new AtomicInteger(0));
    }

    /**
     * 处理断路器状态转换事件
     *
     * @param event              状态转换事件
     * @param circuitBreakerName 断路器名称
     */
    private void handleStateTransition(CircuitBreakerOnStateTransitionEvent event, String circuitBreakerName) {
        CircuitBreaker.State fromState = event.getStateTransition().getFromState();
        CircuitBreaker.State toState = event.getStateTransition().getToState();

        log.info("断路器 [{}] 状态转换: {} -> {}", circuitBreakerName, fromState, toState);

        if (toState == CircuitBreaker.State.HALF_OPEN) {
            successfulProbes.get(circuitBreakerName).set(0);
            log.info("断路器 [{}] 进入半开状态，开始单请求探测", circuitBreakerName);
        }

        if (toState == CircuitBreaker.State.CLOSED) {
            successfulProbes.get(circuitBreakerName).set(0);
            log.info("断路器 [{}] 已关闭，恢复正常流量", circuitBreakerName);
        }

        if (toState == CircuitBreaker.State.OPEN) {
            successfulProbes.get(circuitBreakerName).set(0);
            log.warn("断路器 [{}] 已打开，请求将被快速失败", circuitBreakerName);
        }
    }

    /**
     * 处理断路器成功事件
     * 在半开状态下，成功后动态增加允许的请求数
     *
     * @param event              成功事件
     * @param circuitBreakerName 断路器名称
     * @param circuitBreaker     断路器实例
     */
    private void handleSuccess(io.github.resilience4j.circuitbreaker.event.CircuitBreakerOnSuccessEvent event,
                               String circuitBreakerName,
                               CircuitBreaker circuitBreaker) {
        if (circuitBreaker.getState() == CircuitBreaker.State.HALF_OPEN) {
            AtomicInteger probeCount = successfulProbes.get(circuitBreakerName);
            int currentProbes = probeCount.incrementAndGet();

            log.info("断路器 [{}] 半开状态探测成功，已成功次数: {}", circuitBreakerName, currentProbes);

            int currentPermitted = circuitBreaker.getCircuitBreakerConfig()
                    .getPermittedNumberOfCallsInHalfOpenState();

            int newPermitted = Math.min(currentPermitted * HALF_OPEN_SCALE_FACTOR, MAX_HALF_OPEN_CALLS);

            if (newPermitted > currentPermitted) {
                log.info("断路器 [{}] 半开状态流量递增: {} -> {} (最大: {})",
                        circuitBreakerName, currentPermitted, newPermitted, MAX_HALF_OPEN_CALLS);

                updateCircuitBreakerPermittedCalls(circuitBreaker, newPermitted);
            }
        }
    }

    /**
     * 处理断路器错误事件
     * 在半开状态下，失败后重置探测计数
     *
     * @param event              错误事件
     * @param circuitBreakerName 断路器名称
     * @param circuitBreaker     断路器实例
     */
    private void handleError(io.github.resilience4j.circuitbreaker.event.CircuitBreakerOnErrorEvent event,
                             String circuitBreakerName,
                             CircuitBreaker circuitBreaker) {
        if (circuitBreaker.getState() == CircuitBreaker.State.HALF_OPEN) {
            log.warn("断路器 [{}] 半开状态探测失败，将重置为打开状态", circuitBreakerName);
            successfulProbes.get(circuitBreakerName).set(0);

            updateCircuitBreakerPermittedCalls(circuitBreaker, 1);
        }
    }

    /**
     * 动态更新断路器半开状态允许的请求数
     * 通过反射更新断路器配置
     *
     * @param circuitBreaker    断路器实例
     * @param newPermittedCalls 新的允许请求数
     */
    @SuppressWarnings("unchecked")
    private void updateCircuitBreakerPermittedCalls(CircuitBreaker circuitBreaker, int newPermittedCalls) {
        try {
            io.github.resilience4j.circuitbreaker.CircuitBreakerConfig oldConfig =
                    circuitBreaker.getCircuitBreakerConfig();

            io.github.resilience4j.circuitbreaker.CircuitBreakerConfig newConfig =
                    io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                            .failureRateThreshold(oldConfig.getFailureRateThreshold())
                            .slowCallRateThreshold(oldConfig.getSlowCallRateThreshold())
                            .slowCallDurationThreshold(oldConfig.getSlowCallDurationThreshold())
                            .permittedNumberOfCallsInHalfOpenState(newPermittedCalls)
                            .maxWaitDurationInHalfOpenState(oldConfig.getMaxWaitDurationInHalfOpenState())
                            .slidingWindowType(oldConfig.getSlidingWindowType())
                            .slidingWindowSize(oldConfig.getSlidingWindowSize())
                            .minimumNumberOfCalls(oldConfig.getMinimumNumberOfCalls())
                            .waitDurationInOpenState(oldConfig.getWaitDurationInOpenState())
                            .automaticTransitionFromOpenToHalfOpenEnabled(
                                    oldConfig.isAutomaticTransitionFromOpenToHalfOpenEnabled())
                            .build();

            circuitBreaker.replaceConfig(newConfig);

            log.debug("断路器 [{}] 配置已更新，半开状态允许请求数: {}",
                    circuitBreaker.getName(), newPermittedCalls);

        } catch (Exception e) {
            log.warn("更新断路器 [{}] 配置失败: {}", circuitBreaker.getName(), e.getMessage());
        }
    }
}

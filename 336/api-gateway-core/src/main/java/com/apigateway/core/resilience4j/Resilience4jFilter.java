package com.apigateway.core.resilience4j;

import io.github.resilience4j.bulkhead.Bulkhead;
import io.github.resilience4j.bulkhead.BulkheadRegistry;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.reactor.bulkhead.operator.BulkheadOperator;
import io.github.resilience4j.reactor.circuitbreaker.operator.CircuitBreakerOperator;
import io.github.resilience4j.reactor.ratelimiter.operator.RateLimiterOperator;
import io.github.resilience4j.reactor.timelimiter.operator.TimeLimiterOperator;
import io.github.resilience4j.timelimiter.TimeLimiter;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * Resilience4j全局过滤器
 * 集成断路器、限流、超时控制、隔离舱等弹性模式
 * 根据请求路径匹配不同的服务，应用对应的弹性策略
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class Resilience4jFilter implements GlobalFilter, Ordered {

    private static final int FILTER_ORDER = -100;

    private final CircuitBreakerRegistry circuitBreakerRegistry;
    private final RateLimiterRegistry rateLimiterRegistry;
    private final TimeLimiterRegistry timeLimiterRegistry;
    private final BulkheadRegistry bulkheadRegistry;
    private final FallbackHandler fallbackHandler;

    /**
     * 过滤器执行顺序
     * 优先级设置为-100，确保在路由过滤器之前执行
     *
     * @return 过滤器顺序值
     */
    @Override
    public int getOrder() {
        return FILTER_ORDER;
    }

    /**
     * 执行弹性过滤逻辑
     * 根据请求路径匹配服务类型，应用对应的弹性模式
     * 依次应用：隔离舱 -> 限流 -> 超时 -> 断路器
     *
     * @param exchange 服务器交换对象
     * @param chain    过滤器链
     * @return 响应式Mono对象
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();
        String serviceKey = resolveServiceKey(path);

        log.debug("请求路径: {}, 匹配服务: {}", path, serviceKey);

        CircuitBreaker circuitBreaker = getCircuitBreaker(serviceKey);
        RateLimiter rateLimiter = getRateLimiter(serviceKey);
        TimeLimiter timeLimiter = getTimeLimiter(serviceKey);
        Bulkhead bulkhead = getBulkhead(serviceKey);

        return chain.filter(exchange)
                .transformDeferred(BulkheadOperator.of(bulkhead))
                .transformDeferred(RateLimiterOperator.of(rateLimiter))
                .transformDeferred(TimeLimiterOperator.of(timeLimiter))
                .transformDeferred(CircuitBreakerOperator.of(circuitBreaker))
                .onErrorResume(throwable -> {
                    log.error("服务调用异常，服务: {}, 异常: {}", serviceKey, throwable.getMessage());
                    return fallbackHandler.handleFallback(exchange, serviceKey, throwable);
                });
    }

    /**
     * 根据请求路径解析服务标识
     * 支持REST、gRPC、GraphQL、聚合等多种服务类型
     *
     * @param path 请求路径
     * @return 服务标识
     */
    private String resolveServiceKey(String path) {
        if (path.startsWith("/api/rest/")) {
            return "restService";
        } else if (path.startsWith("/api/grpc/")) {
            return "grpcService";
        } else if (path.startsWith("/api/graphql/")) {
            return "graphqlService";
        } else if (path.startsWith("/api/aggregate/")) {
            return "aggregateService";
        }
        return "default";
    }

    /**
     * 获取断路器实例
     * 如果指定服务不存在，则返回默认断路器
     *
     * @param serviceKey 服务标识
     * @return 断路器实例
     */
    private CircuitBreaker getCircuitBreaker(String serviceKey) {
        try {
            return circuitBreakerRegistry.circuitBreaker(serviceKey);
        } catch (Exception e) {
            log.warn("未找到服务 {} 的断路器配置，使用默认配置", serviceKey);
            return circuitBreakerRegistry.circuitBreaker("default");
        }
    }

    /**
     * 获取限流器实例
     * 如果指定服务不存在，则返回默认限流器
     *
     * @param serviceKey 服务标识
     * @return 限流器实例
     */
    private RateLimiter getRateLimiter(String serviceKey) {
        try {
            return rateLimiterRegistry.rateLimiter(serviceKey);
        } catch (Exception e) {
            log.warn("未找到服务 {} 的限流器配置，使用默认配置", serviceKey);
            return rateLimiterRegistry.rateLimiter("default");
        }
    }

    /**
     * 获取超时限制器实例
     * 如果指定服务不存在，则返回默认超时限制器
     *
     * @param serviceKey 服务标识
     * @return 超时限制器实例
     */
    private TimeLimiter getTimeLimiter(String serviceKey) {
        try {
            return timeLimiterRegistry.timeLimiter(serviceKey);
        } catch (Exception e) {
            log.warn("未找到服务 {} 的超时限制器配置，使用默认配置", serviceKey);
            return timeLimiterRegistry.timeLimiter("default");
        }
    }

    /**
     * 获取隔离舱实例
     * 如果指定服务不存在，则返回默认隔离舱
     *
     * @param serviceKey 服务标识
     * @return 隔离舱实例
     */
    private Bulkhead getBulkhead(String serviceKey) {
        try {
            return bulkheadRegistry.bulkhead(serviceKey);
        } catch (Exception e) {
            log.warn("未找到服务 {} 的隔离舱配置，使用默认配置", serviceKey);
            return bulkheadRegistry.bulkhead("default");
        }
    }
}

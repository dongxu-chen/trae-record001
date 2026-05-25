package com.apigateway.core.resilience4j;

import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * 限流器配置类
 * 基于令牌桶算法，为不同服务配置限流规则
 * 控制单位时间内的请求数量，防止服务被流量冲垮
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Configuration
public class RateLimiterConfig {

    /**
     * REST服务限流器
     * 每秒允许100个请求，令牌桶大小为200
     * 限流周期为1秒，超时等待时间为500毫秒
     *
     * @param registry 限流器注册中心
     * @return REST服务限流器实例
     */
    @Bean
    public RateLimiter restServiceRateLimiter(RateLimiterRegistry registry) {
        io.github.resilience4j.ratelimiter.RateLimiterConfig config = io.github.resilience4j.ratelimiter.RateLimiterConfig.custom()
                .limitForPeriod(100)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .timeoutDuration(Duration.ofMillis(500))
                .build();
        return registry.rateLimiter("restService", config);
    }

    /**
     * gRPC服务限流器
     * 每秒允许200个请求，令牌桶大小为400
     * 限流周期为1秒，超时等待时间为300毫秒
     *
     * @param registry 限流器注册中心
     * @return gRPC服务限流器实例
     */
    @Bean
    public RateLimiter grpcServiceRateLimiter(RateLimiterRegistry registry) {
        io.github.resilience4j.ratelimiter.RateLimiterConfig config = io.github.resilience4j.ratelimiter.RateLimiterConfig.custom()
                .limitForPeriod(200)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .timeoutDuration(Duration.ofMillis(300))
                .build();
        return registry.rateLimiter("grpcService", config);
    }

    /**
     * GraphQL服务限流器
     * 每秒允许50个请求，令牌桶大小为100
     * 限流周期为1秒，超时等待时间为800毫秒
     *
     * @param registry 限流器注册中心
     * @return GraphQL服务限流器实例
     */
    @Bean
    public RateLimiter graphqlServiceRateLimiter(RateLimiterRegistry registry) {
        io.github.resilience4j.ratelimiter.RateLimiterConfig config = io.github.resilience4j.ratelimiter.RateLimiterConfig.custom()
                .limitForPeriod(50)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .timeoutDuration(Duration.ofMillis(800))
                .build();
        return registry.rateLimiter("graphqlService", config);
    }

    /**
     * 聚合服务限流器
     * 每秒允许30个请求，令牌桶大小为60
     * 限流周期为1秒，超时等待时间为1000毫秒
     *
     * @param registry 限流器注册中心
     * @return 聚合服务限流器实例
     */
    @Bean
    public RateLimiter aggregateServiceRateLimiter(RateLimiterRegistry registry) {
        io.github.resilience4j.ratelimiter.RateLimiterConfig config = io.github.resilience4j.ratelimiter.RateLimiterConfig.custom()
                .limitForPeriod(30)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .timeoutDuration(Duration.ofMillis(1000))
                .build();
        return registry.rateLimiter("aggregateService", config);
    }

    /**
     * 全局默认限流器
     * 每秒允许500个请求，令牌桶大小为1000
     * 用于未匹配到特定服务的通用限流
     *
     * @param registry 限流器注册中心
     * @return 默认限流器实例
     */
    @Bean
    public RateLimiter defaultRateLimiter(RateLimiterRegistry registry) {
        io.github.resilience4j.ratelimiter.RateLimiterConfig config = io.github.resilience4j.ratelimiter.RateLimiterConfig.custom()
                .limitForPeriod(500)
                .limitRefreshPeriod(Duration.ofSeconds(1))
                .timeoutDuration(Duration.ofMillis(100))
                .build();
        return registry.rateLimiter("default", config);
    }
}

package com.apigateway.core.resilience4j;

import io.github.resilience4j.timelimiter.TimeLimiter;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * 超时控制配置类
 * 为不同服务配置超时时间，防止请求长时间阻塞
 * 超时后自动中断请求并触发降级
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Configuration
public class TimeLimiterConfig {

    /**
     * REST服务超时限制
     * 超时时间为3秒，允许取消正在执行的异步调用
     *
     * @param registry 超时限制器注册中心
     * @return REST服务超时限制器实例
     */
    @Bean
    public TimeLimiter restServiceTimeLimiter(TimeLimiterRegistry registry) {
        io.github.resilience4j.timelimiter.TimeLimiterConfig config = io.github.resilience4j.timelimiter.TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(3))
                .cancelRunningFuture(true)
                .build();
        return registry.timeLimiter("restService", config);
    }

    /**
     * gRPC服务超时限制
     * 超时时间为5秒，允许取消正在执行的异步调用
     *
     * @param registry 超时限制器注册中心
     * @return gRPC服务超时限制器实例
     */
    @Bean
    public TimeLimiter grpcServiceTimeLimiter(TimeLimiterRegistry registry) {
        io.github.resilience4j.timelimiter.TimeLimiterConfig config = io.github.resilience4j.timelimiter.TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(5))
                .cancelRunningFuture(true)
                .build();
        return registry.timeLimiter("grpcService", config);
    }

    /**
     * GraphQL服务超时限制
     * 超时时间为10秒，允许取消正在执行的异步调用
     *
     * @param registry 超时限制器注册中心
     * @return GraphQL服务超时限制器实例
     */
    @Bean
    public TimeLimiter graphqlServiceTimeLimiter(TimeLimiterRegistry registry) {
        io.github.resilience4j.timelimiter.TimeLimiterConfig config = io.github.resilience4j.timelimiter.TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(10))
                .cancelRunningFuture(true)
                .build();
        return registry.timeLimiter("graphqlService", config);
    }

    /**
     * 聚合服务超时限制
     * 超时时间为15秒，允许取消正在执行的异步调用
     *
     * @param registry 超时限制器注册中心
     * @return 聚合服务超时限制器实例
     */
    @Bean
    public TimeLimiter aggregateServiceTimeLimiter(TimeLimiterRegistry registry) {
        io.github.resilience4j.timelimiter.TimeLimiterConfig config = io.github.resilience4j.timelimiter.TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(15))
                .cancelRunningFuture(true)
                .build();
        return registry.timeLimiter("aggregateService", config);
    }

    /**
     * 默认超时限制
     * 超时时间为8秒，用于未匹配到特定服务的通用超时控制
     *
     * @param registry 超时限制器注册中心
     * @return 默认超时限制器实例
     */
    @Bean
    public TimeLimiter defaultTimeLimiter(TimeLimiterRegistry registry) {
        io.github.resilience4j.timelimiter.TimeLimiterConfig config = io.github.resilience4j.timelimiter.TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(8))
                .cancelRunningFuture(true)
                .build();
        return registry.timeLimiter("default", config);
    }
}

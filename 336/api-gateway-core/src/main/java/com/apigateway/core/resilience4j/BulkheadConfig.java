package com.apigateway.core.resilience4j;

import io.github.resilience4j.bulkhead.Bulkhead;
import io.github.resilience4j.bulkhead.BulkheadRegistry;
import io.github.resilience4j.bulkhead.ThreadPoolBulkhead;
import io.github.resilience4j.bulkhead.ThreadPoolBulkheadRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * 隔离舱配置类
 * 控制并发请求数量，防止某个服务占用过多资源
 * 提供信号量隔离和线程池隔离两种方式
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Configuration
public class BulkheadConfig {

    /**
     * REST服务信号量隔离舱
     * 最大并发请求数为100，等待时间为100毫秒
     *
     * @param registry 隔离舱注册中心
     * @return REST服务隔离舱实例
     */
    @Bean
    public Bulkhead restServiceBulkhead(BulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.BulkheadConfig config = io.github.resilience4j.bulkhead.BulkheadConfig.custom()
                .maxConcurrentCalls(100)
                .maxWaitDuration(Duration.ofMillis(100))
                .build();
        return registry.bulkhead("restService", config);
    }

    /**
     * gRPC服务信号量隔离舱
     * 最大并发请求数为200，等待时间为50毫秒
     *
     * @param registry 隔离舱注册中心
     * @return gRPC服务隔离舱实例
     */
    @Bean
    public Bulkhead grpcServiceBulkhead(BulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.BulkheadConfig config = io.github.resilience4j.bulkhead.BulkheadConfig.custom()
                .maxConcurrentCalls(200)
                .maxWaitDuration(Duration.ofMillis(50))
                .build();
        return registry.bulkhead("grpcService", config);
    }

    /**
     * GraphQL服务信号量隔离舱
     * 最大并发请求数为50，等待时间为200毫秒
     *
     * @param registry 隔离舱注册中心
     * @return GraphQL服务隔离舱实例
     */
    @Bean
    public Bulkhead graphqlServiceBulkhead(BulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.BulkheadConfig config = io.github.resilience4j.bulkhead.BulkheadConfig.custom()
                .maxConcurrentCalls(50)
                .maxWaitDuration(Duration.ofMillis(200))
                .build();
        return registry.bulkhead("graphqlService", config);
    }

    /**
     * 聚合服务信号量隔离舱
     * 最大并发请求数为30，等待时间为300毫秒
     *
     * @param registry 隔离舱注册中心
     * @return 聚合服务隔离舱实例
     */
    @Bean
    public Bulkhead aggregateServiceBulkhead(BulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.BulkheadConfig config = io.github.resilience4j.bulkhead.BulkheadConfig.custom()
                .maxConcurrentCalls(30)
                .maxWaitDuration(Duration.ofMillis(300))
                .build();
        return registry.bulkhead("aggregateService", config);
    }

    /**
     * REST服务线程池隔离舱
     * 核心线程数10，最大线程数20，队列容量50
     * 空闲线程存活时间60秒
     *
     * @param registry 线程池隔离舱注册中心
     * @return REST服务线程池隔离舱实例
     */
    @Bean
    public ThreadPoolBulkhead restServiceThreadPoolBulkhead(ThreadPoolBulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.ThreadPoolBulkheadConfig config = io.github.resilience4j.bulkhead.ThreadPoolBulkheadConfig.custom()
                .coreThreadPoolSize(10)
                .maxThreadPoolSize(20)
                .queueCapacity(50)
                .keepAliveDuration(Duration.ofSeconds(60))
                .build();
        return registry.threadPoolBulkhead("restService", config);
    }

    /**
     * gRPC服务线程池隔离舱
     * 核心线程数20，最大线程数40，队列容量100
     * 空闲线程存活时间60秒
     *
     * @param registry 线程池隔离舱注册中心
     * @return gRPC服务线程池隔离舱实例
     */
    @Bean
    public ThreadPoolBulkhead grpcServiceThreadPoolBulkhead(ThreadPoolBulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.ThreadPoolBulkheadConfig config = io.github.resilience4j.bulkhead.ThreadPoolBulkheadConfig.custom()
                .coreThreadPoolSize(20)
                .maxThreadPoolSize(40)
                .queueCapacity(100)
                .keepAliveDuration(Duration.ofSeconds(60))
                .build();
        return registry.threadPoolBulkhead("grpcService", config);
    }

    /**
     * 默认信号量隔离舱
     * 最大并发请求数为500，等待时间为50毫秒
     * 用于未匹配到特定服务的通用隔离
     *
     * @param registry 隔离舱注册中心
     * @return 默认隔离舱实例
     */
    @Bean
    public Bulkhead defaultBulkhead(BulkheadRegistry registry) {
        io.github.resilience4j.bulkhead.BulkheadConfig config = io.github.resilience4j.bulkhead.BulkheadConfig.custom()
                .maxConcurrentCalls(500)
                .maxWaitDuration(Duration.ofMillis(50))
                .build();
        return registry.bulkhead("default", config);
    }
}

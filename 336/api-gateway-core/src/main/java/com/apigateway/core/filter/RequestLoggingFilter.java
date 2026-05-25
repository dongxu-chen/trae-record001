package com.apigateway.core.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;

/**
 * 全局请求日志过滤器
 * 记录所有经过网关的请求和响应信息，包括请求路径、方法、状态码、耗时等
 * 采用响应式编程风格，不阻塞请求处理流程
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
public class RequestLoggingFilter implements GlobalFilter, Ordered {

    /**
     * 过滤器执行顺序
     * 数值越小，优先级越高
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }

    /**
     * 执行过滤器逻辑
     * 在请求进入时记录开始时间，在响应返回时计算耗时并记录完整日志
     *
     * @param exchange 服务器Web交换对象，包含请求和响应信息
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        Instant startTime = Instant.now();
        String requestPath = exchange.getRequest().getURI().getPath();
        String requestMethod = exchange.getRequest().getMethod().name();
        String clientIp = exchange.getRequest().getRemoteAddress() != null
                ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
                : "unknown";

        log.info("请求开始 - 方法: {}, 路径: {}, 客户端IP: {}", requestMethod, requestPath, clientIp);

        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    int statusCode = exchange.getResponse().getStatusCode() != null
                            ? exchange.getResponse().getStatusCode().value()
                            : 0;
                    long duration = java.time.Duration.between(startTime, Instant.now()).toMillis();

                    log.info("请求结束 - 方法: {}, 路径: {}, 状态码: {}, 耗时: {}ms",
                            requestMethod, requestPath, statusCode, duration);
                }));
    }
}

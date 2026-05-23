package com.gateway.plugin.impl;

import com.gateway.plugin.GatewayPlugin;
import com.gateway.plugin.PluginChain;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class AuditLogPlugin implements GatewayPlugin {

    private final ReactiveRedisTemplate<String, Object> reactiveRedisTemplate;

    public AuditLogPlugin(ReactiveRedisTemplate<String, Object> reactiveRedisTemplate) {
        this.reactiveRedisTemplate = reactiveRedisTemplate;
    }

    @Override
    public Mono<Void> execute(ServerWebExchange exchange, PluginChain chain) {
        log.debug("Executing AuditLogPlugin");

        ServerHttpRequest request = exchange.getRequest();
        String userId = exchange.getAttribute("userId");
        String path = request.getURI().getPath();
        String method = request.getMethod() != null ? request.getMethod().name() : "UNKNOWN";
        String clientIp = request.getRemoteAddress() != null
                ? request.getRemoteAddress().getAddress().getHostAddress()
                : "unknown";
        String requestId = exchange.getAttribute("requestId");

        if (userId == null) {
            userId = "anonymous";
        }

        Map<String, Object> auditLog = new HashMap<>();
        auditLog.put("userId", userId);
        auditLog.put("path", path);
        auditLog.put("method", method);
        auditLog.put("clientIp", clientIp);
        auditLog.put("requestId", requestId);
        auditLog.put("timestamp", System.currentTimeMillis());

        String key = "audit:log:" + userId + ":" + System.currentTimeMillis();

        return reactiveRedisTemplate.opsForValue()
                .set(key, auditLog, Duration.ofDays(7))
                .doOnError(e -> log.warn("Failed to save audit log to Redis", e))
                .onErrorResume(e -> Mono.empty())
                .then(chain.doFilter(exchange));
    }

    @Override
    public int getOrder() {
        return 20;
    }

    @Override
    public String getName() {
        return "AuditLogPlugin";
    }
}

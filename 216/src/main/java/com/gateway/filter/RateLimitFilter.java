package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Collections;
import java.util.List;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class RateLimitFilter implements GlobalFilter, Ordered {

    private final ReactiveRedisTemplate<String, Object> reactiveRedisTemplate;
    private final GatewayProperties gatewayProperties;

    private static final String SLIDING_WINDOW_SCRIPT = """
            local key = KEYS[1]
            local windowSize = tonumber(ARGV[1])
            local maxRequests = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local requestId = ARGV[4]
            
            local windowStart = now - (windowSize * 1000)
            
            redis.call('ZREMRANGEBYSCORE', key, 0, windowStart)
            
            local currentCount = redis.call('ZCARD', key)
            
            if currentCount < maxRequests then
                redis.call('ZADD', key, now, requestId)
                redis.call('EXPIRE', key, windowSize + 1)
                return 1
            else
                return 0
            end
            """;

    private final RedisScript<Long> slidingWindowScript = new DefaultRedisScript<>(SLIDING_WINDOW_SCRIPT, Long.class);

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!gatewayProperties.getRateLimit().isEnabled()) {
            return chain.filter(exchange);
        }

        String userId = getUserId(exchange);
        String key = "rate_limit:sliding_window:" + userId;

        int windowSize = gatewayProperties.getRateLimit().getWindowSizeInSeconds();
        int maxRequests = gatewayProperties.getRateLimit().getRequestsPerSecond();
        long now = System.currentTimeMillis();
        String requestId = UUID.randomUUID().toString();

        List<String> keys = Collections.singletonList(key);
        Object[] args = {String.valueOf(windowSize), String.valueOf(maxRequests), String.valueOf(now), requestId};

        return reactiveRedisTemplate.execute(slidingWindowScript, keys, args)
                .next()
                .flatMap(result -> {
                    if (result == 1L) {
                        log.debug("Rate limit passed for user: {}, window: {}s, max: {}", userId, windowSize, maxRequests);
                        return chain.filter(exchange);
                    } else {
                        log.warn("Rate limit exceeded for user: {}, limit: {} requests/{}s", userId, maxRequests, windowSize);
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        exchange.getResponse().getHeaders().add("X-RateLimit-Limit", String.valueOf(maxRequests));
                        exchange.getResponse().getHeaders().add("X-RateLimit-Window", windowSize + "s");
                        exchange.getResponse().getHeaders().add("X-RateLimit-Retry-After", String.valueOf(windowSize));
                        return exchange.getResponse().setComplete();
                    }
                })
                .onErrorResume(e -> {
                    log.error("Rate limit check error for user: {}", userId, e);
                    return chain.filter(exchange);
                });
    }

    private String getUserId(ServerWebExchange exchange) {
        Object userIdAttr = exchange.getAttribute("userId");
        if (userIdAttr != null) {
            return userIdAttr.toString();
        }

        ServerHttpRequest request = exchange.getRequest();
        String clientIp = request.getRemoteAddress() != null
                ? request.getRemoteAddress().getAddress().getHostAddress()
                : "unknown";

        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            clientIp = xForwardedFor.split(",")[0].trim();
        }

        return "ip:" + clientIp;
    }

    @Override
    public int getOrder() {
        return -50;
    }
}

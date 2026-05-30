package com.apiversion.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Random;

@Slf4j
@Component
@RequiredArgsConstructor
public class GrayReleaseFilter implements GlobalFilter, Ordered {

    private final ReactiveStringRedisTemplate redisTemplate;

    private static final String GRAY_HEADER = "X-Gray-Release";
    private static final String USER_ID_HEADER = "X-User-Id";
    private static final String GRAY_CONFIG_KEY = "api:gray:config:";
    private static final String GRAY_USERS_KEY = "api:gray:users:";
    private static final Random RANDOM = new Random();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String userId = request.getHeaders().getFirst(USER_ID_HEADER);

        return isGrayUser(path, userId)
                .switchIfEmpty(isGrayByPercentage(path))
                .defaultIfEmpty(false)
                .flatMap(isGray -> {
                    if (isGray) {
                        log.debug("灰度发布生效 - 路径: {}, 用户: {}", path, userId);
                        ServerHttpRequest modifiedRequest = request.mutate()
                                .header(GRAY_HEADER, "true")
                                .build();
                        return chain.filter(exchange.mutate()
                                .request(modifiedRequest)
                                .build());
                    }
                    return chain.filter(exchange);
                });
    }

    private Mono<Boolean> isGrayUser(String path, String userId) {
        if (userId == null || userId.isEmpty()) {
            return Mono.empty();
        }
        return redisTemplate.opsForSet()
                .isMember(GRAY_USERS_KEY + path, userId)
                .filter(isMember -> isMember)
                .map(isMember -> {
                    log.debug("灰度用户匹配 - 用户: {}, 路径: {}", userId, path);
                    return true;
                });
    }

    private Mono<Boolean> isGrayByPercentage(String path) {
        return redisTemplate.opsForValue()
                .get(GRAY_CONFIG_KEY + path)
                .defaultIfEmpty("0")
                .map(percentageStr -> {
                    try {
                        int percentage = Integer.parseInt(percentageStr);
                        if (percentage <= 0) {
                            return false;
                        }
                        if (percentage >= 100) {
                            return true;
                        }
                        int random = RANDOM.nextInt(100);
                        boolean isGray = random < percentage;
                        log.debug("灰度流量比例 - 路径: {}, 比例: {}%, 随机值: {}, 结果: {}", 
                                path, percentage, random, isGray);
                        return isGray;
                    } catch (NumberFormatException e) {
                        log.warn("灰度比例配置格式错误: {}", percentageStr);
                        return false;
                    }
                });
    }

    @Override
    public int getOrder() {
        return -90;
    }
}

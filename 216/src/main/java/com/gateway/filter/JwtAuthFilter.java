package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import com.gateway.service.JwtBlacklistService;
import com.gateway.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthFilter implements GlobalFilter, Ordered {

    private final JwtUtil jwtUtil;
    private final GatewayProperties gatewayProperties;
    private final JwtBlacklistService jwtBlacklistService;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        if (isExcludedPath(path)) {
            return chain.filter(exchange);
        }

        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            log.warn("Missing or invalid Authorization header for path: {}", path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = authHeader.substring(7);

        if (!jwtUtil.validateToken(token)) {
            log.warn("Invalid or expired token for path: {}", path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        return jwtBlacklistService.isBlacklisted(token)
                .flatMap(isBlacklisted -> {
                    if (isBlacklisted) {
                        log.warn("Token is blacklisted for path: {}", path);
                        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
                        return exchange.getResponse().setComplete();
                    }

                    String userId = jwtUtil.extractUserId(token);
                    String username = jwtUtil.extractUsername(token);

                    ServerHttpRequest modifiedRequest = request.mutate()
                            .header("X-User-Id", userId)
                            .header("X-Username", username)
                            .build();

                    exchange.getAttributes().put("userId", userId);
                    exchange.getAttributes().put("username", username);
                    exchange.getAttributes().put("token", token);

                    return chain.filter(exchange.mutate().request(modifiedRequest).build());
                });
    }

    private boolean isExcludedPath(String path) {
        return gatewayProperties.getAuth().getExcludePaths().stream()
                .anyMatch(pattern -> path.matches(pattern.replace("**", ".*")));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}

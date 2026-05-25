package com.apigateway.core.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Base64;
import java.util.List;

/**
 * 简单认证过滤器
 * 支持两种认证模式：
 * 1. 简单API Key认证（默认）- 通过X-API-Key请求头验证
 * 2. JWT认证（可选）- 通过Authorization: Bearer {token}请求头验证
 * 可通过配置文件开启/关闭认证，以及配置白名单路径
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
public class AuthenticationFilter implements GlobalFilter, Ordered {

    private static final String API_KEY_HEADER = "X-API-Key";
    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    @Value("${gateway.auth.enabled:true}")
    private boolean authEnabled;

    @Value("${gateway.auth.mode:api-key}")
    private String authMode;

    @Value("${gateway.auth.api-key:gateway-demo-key}")
    private String apiKey;

    @Value("${gateway.auth.whitelist:/actuator/**,/api/public/**}")
    private List<String> whitelist;

    /**
     * 过滤器执行顺序
     * 在日志过滤器之后，其他业务过滤器之前执行
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 100;
    }

    /**
     * 执行认证过滤
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        if (!authEnabled || isWhitelisted(path)) {
            log.debug("跳过认证 - 路径: {}, 认证启用: {}, 白名单匹配: {}",
                    path, authEnabled, isWhitelisted(path));
            return chain.filter(exchange);
        }

        return switch (authMode.toLowerCase()) {
            case "jwt" -> authenticateJwt(exchange, chain);
            case "api-key" -> authenticateApiKey(exchange, chain);
            default -> authenticateApiKey(exchange, chain);
        };
    }

    /**
     * 检查请求路径是否在白名单中
     *
     * @param path 请求路径
     * @return 是否在白名单中
     */
    private boolean isWhitelisted(String path) {
        return whitelist.stream()
                .anyMatch(pattern -> path.matches(pattern.replace("**", ".*")));
    }

    /**
     * API Key认证
     * 验证X-API-Key请求头是否匹配配置的API Key
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    private Mono<Void> authenticateApiKey(ServerWebExchange exchange, GatewayFilterChain chain) {
        String requestApiKey = exchange.getRequest().getHeaders().getFirst(API_KEY_HEADER);

        if (requestApiKey == null || requestApiKey.isEmpty()) {
            log.warn("API Key缺失 - 路径: {}", exchange.getRequest().getURI().getPath());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        if (!apiKey.equals(requestApiKey)) {
            log.warn("API Key无效 - 路径: {}", exchange.getRequest().getURI().getPath());
            exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
            return exchange.getResponse().setComplete();
        }

        log.debug("API Key认证通过 - 路径: {}", exchange.getRequest().getURI().getPath());
        return chain.filter(exchange);
    }

    /**
     * JWT认证（简化版）
     * 验证Authorization请求头中的Bearer Token格式
     * 实际生产环境应使用完整的JWT库进行签名验证
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    private Mono<Void> authenticateJwt(ServerWebExchange exchange, GatewayFilterChain chain) {
        String authHeader = exchange.getRequest().getHeaders().getFirst(AUTHORIZATION_HEADER);

        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            log.warn("JWT Token缺失或格式错误 - 路径: {}", exchange.getRequest().getURI().getPath());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = authHeader.substring(BEARER_PREFIX.length());

        if (!validateJwtToken(token)) {
            log.warn("JWT Token无效 - 路径: {}", exchange.getRequest().getURI().getPath());
            exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
            return exchange.getResponse().setComplete();
        }

        String userId = extractUserIdFromJwt(token);
        ServerHttpRequest modifiedRequest = exchange.getRequest().mutate()
                .header("X-User-Id", userId)
                .build();

        log.debug("JWT认证通过 - 用户ID: {}, 路径: {}", userId, exchange.getRequest().getURI().getPath());
        return chain.filter(exchange.mutate().request(modifiedRequest).build());
    }

    /**
     * 简化的JWT Token验证
     * 实际生产环境应使用JJWT或Nimbus等库进行完整验证
     *
     * @param token JWT Token
     * @return Token是否有效
     */
    private boolean validateJwtToken(String token) {
        try {
            String[] parts = token.split("\\.");
            if (parts.length != 3) {
                return false;
            }
            Base64.getUrlDecoder().decode(parts[0]);
            Base64.getUrlDecoder().decode(parts[1]);
            return true;
        } catch (Exception e) {
            log.error("JWT Token验证失败: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 从JWT Token中提取用户ID
     *
     * @param token JWT Token
     * @return 用户ID
     */
    private String extractUserIdFromJwt(String token) {
        try {
            String[] parts = token.split("\\.");
            String payload = new String(Base64.getUrlDecoder().decode(parts[1]));
            if (payload.contains("\"sub\":\"")) {
                int start = payload.indexOf("\"sub\":\"") + 7;
                int end = payload.indexOf("\"", start);
                return payload.substring(start, end);
            }
            return "anonymous";
        } catch (Exception e) {
            log.error("提取用户ID失败: {}", e.getMessage());
            return "anonymous";
        }
    }
}

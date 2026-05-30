package com.apiversion.gateway.filter;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class DeprecationInterceptorFilter implements GlobalFilter, Ordered {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String VERSION_HEADER = "X-API-Version";
    private static final String CLIENT_VERSION_HEADER = "X-Client-Version";
    private static final String DEPRECATION_CONFIG_KEY = "api:deprecation:config:";
    private static final String DEPRECATION_WARNING_HEADER = "X-API-Deprecation-Warning";
    private static final String DEPRECATION_DATE_HEADER = "X-API-Retire-Date";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String apiVersion = request.getHeaders().getFirst(VERSION_HEADER);
        String clientVersion = request.getHeaders().getFirst(CLIENT_VERSION_HEADER);

        if (apiVersion == null) {
            apiVersion = "v1";
        }

        String serviceName = extractServiceName(path);
        if (serviceName == null) {
            return chain.filter(exchange);
        }

        String finalApiVersion = apiVersion;
        return getDeprecationConfig(serviceName, apiVersion)
                .flatMap(config -> {
                    if (config == null) {
                        return chain.filter(exchange);
                    }

                    ServerHttpResponse response = exchange.getResponse();

                    if (config.isExpired()) {
                        log.warn("API版本已超期，拒绝访问: service={}, version={}, path={}",
                                serviceName, finalApiVersion, path);
                        return handleExpiredVersion(response, config, serviceName, finalApiVersion, clientVersion);
                    }

                    if (config.isDeprecated()) {
                        long daysRemaining = config.getDaysUntilRetirement();
                        log.info("API版本已废弃，剩余{}天下线: service={}, version={}, path={}",
                                daysRemaining, serviceName, finalApiVersion, path);

                        addDeprecationHeaders(response, config);

                        if (daysRemaining <= 7) {
                            response.getHeaders().add(DEPRECATION_WARNING_HEADER,
                                    String.format("WARNING: This API version will retire in %d days. %s",
                                            daysRemaining, config.getMessage()));
                        }
                    }

                    return chain.filter(exchange);
                });
    }

    private Mono<DeprecationConfig> getDeprecationConfig(String serviceName, String version) {
        String cacheKey = DEPRECATION_CONFIG_KEY + serviceName + ":" + version;
        return redisTemplate.opsForValue().get(cacheKey)
                .map(json -> {
                    try {
                        return objectMapper.readValue(json, DeprecationConfig.class);
                    } catch (Exception e) {
                        log.warn("解析废弃配置失败: {}", e.getMessage());
                        return null;
                    }
                })
                .defaultIfEmpty(null);
    }

    private String extractServiceName(String path) {
        String[] parts = path.split("/");
        if (parts.length >= 3 && "api".equals(parts[1])) {
            return parts[2];
        }
        return null;
    }

    private Mono<Void> handleExpiredVersion(ServerHttpResponse response, DeprecationConfig config,
                                            String serviceName, String version, String clientVersion) {
        response.setStatusCode(HttpStatus.GONE);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        response.getHeaders().add(DEPRECATION_DATE_HEADER,
                config.getPlannedRetireTime() != null ? config.getPlannedRetireTime().toString() : "");
        response.getHeaders().add(DEPRECATION_WARNING_HEADER,
                "ERROR: This API version has been retired. " + config.getMessage());

        Map<String, Object> errorBody = new HashMap<>();
        errorBody.put("code", 410);
        errorBody.put("message", "API版本已退役");
        errorBody.put("service", serviceName);
        errorBody.put("version", version);
        errorBody.put("clientVersion", clientVersion);
        errorBody.put("retiredAt", config.getPlannedRetireTime() != null ? config.getPlannedRetireTime().toString() : "");
        errorBody.put("upgradeGuide", config.getMessage());
        errorBody.put("latestVersion", config.getLatestVersion());
        errorBody.put("upgradeUrl", config.getUpgradeUrl());

        try {
            byte[] bytes = objectMapper.writeValueAsBytes(errorBody);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            return response.writeWith(Mono.just(buffer));
        } catch (Exception e) {
            log.error("序列化错误响应失败", e);
            String errorMsg = "{\"code\":410,\"message\":\"API版本已退役，请升级到最新版本\"}";
            byte[] bytes = errorMsg.getBytes(StandardCharsets.UTF_8);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            return response.writeWith(Mono.just(buffer));
        }
    }

    private void addDeprecationHeaders(ServerHttpResponse response, DeprecationConfig config) {
        if (config.getPlannedRetireTime() != null) {
            response.getHeaders().add(DEPRECATION_DATE_HEADER, config.getPlannedRetireTime().toString());
        }
        if (config.getMessage() != null) {
            response.getHeaders().add(DEPRECATION_WARNING_HEADER,
                    String.format("DEPRECATED: %s", config.getMessage()));
        }
    }

    @Override
    public int getOrder() {
        return -90;
    }

    @lombok.Data
    public static class DeprecationConfig {
        private String serviceName;
        private String version;
        private String status;
        private LocalDateTime deprecateTime;
        private LocalDateTime plannedRetireTime;
        private String message;
        private String latestVersion;
        private String upgradeUrl;

        public boolean isDeprecated() {
            return "DEPRECATED".equals(status) || "OFFLINE".equals(status);
        }

        public boolean isExpired() {
            if (plannedRetireTime == null) {
                return false;
            }
            return LocalDateTime.now().isAfter(plannedRetireTime);
        }

        public long getDaysUntilRetirement() {
            if (plannedRetireTime == null) {
                return -1;
            }
            return ChronoUnit.DAYS.between(LocalDateTime.now(), plannedRetireTime);
        }
    }
}

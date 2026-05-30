package com.apiversion.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@RequiredArgsConstructor
public class MetricsFilter implements GlobalFilter, Ordered {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String METRICS_TOTAL_KEY = "api:metrics:total:";
    private static final String METRICS_SUCCESS_KEY = "api:metrics:success:";
    private static final String METRICS_FAIL_KEY = "api:metrics:fail:";
    private static final String METRICS_TIME_KEY = "api:metrics:time:";
    private static final String METRICS_VERSION_KEY = "api:metrics:version:";
    private static final String METRICS_CLIENT_KEY = "api:metrics:client:";
    private static final String START_TIME_ATTR = "startTime";
    private static final String VERSION_HEADER = "X-API-Version";
    private static final String CLIENT_VERSION_HEADER = "X-Client-Version";
    private static final String USER_AGENT_HEADER = "User-Agent";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String method = request.getMethod().name();
        String apiVersion = request.getHeaders().getFirst(VERSION_HEADER);
        String clientVersion = request.getHeaders().getFirst(CLIENT_VERSION_HEADER);
        String userAgent = request.getHeaders().getFirst(USER_AGENT_HEADER);
        String today = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String statDate = LocalDate.now().toString();

        if (apiVersion == null) {
            apiVersion = "v1";
        }

        exchange.getAttributes().put(START_TIME_ATTR, System.currentTimeMillis());

        String finalApiVersion = apiVersion;
        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    recordMetrics(exchange, path, method, today, statDate, finalApiVersion, clientVersion, userAgent, true);
                }))
                .onErrorResume(e -> {
                    recordMetrics(exchange, path, method, today, statDate, finalApiVersion, clientVersion, userAgent, false);
                    return Mono.error(e);
                });
    }

    private void recordMetrics(ServerWebExchange exchange, String path, String method, String date, String statDate,
                               String apiVersion, String clientVersion, String userAgent, boolean success) {
        Long startTime = exchange.getAttribute(START_TIME_ATTR);
        long responseTime = startTime != null ? System.currentTimeMillis() - startTime : 0;

        String keyPrefix = method + ":" + path;
        String serviceName = extractServiceName(path);

        redisTemplate.opsForValue()
                .increment(METRICS_TOTAL_KEY + date + ":" + keyPrefix)
                .subscribe();

        if (success) {
            ServerHttpResponse response = exchange.getResponse();
            int statusCode = response.getStatusCode() != null ? response.getStatusCode().value() : 200;

            if (statusCode < 500) {
                redisTemplate.opsForValue()
                        .increment(METRICS_SUCCESS_KEY + date + ":" + keyPrefix)
                        .subscribe();
            } else {
                redisTemplate.opsForValue()
                        .increment(METRICS_FAIL_KEY + date + ":" + keyPrefix)
                        .subscribe();
            }
        } else {
            redisTemplate.opsForValue()
                    .increment(METRICS_FAIL_KEY + date + ":" + keyPrefix)
                    .subscribe();
        }

        redisTemplate.opsForList()
                .rightPush(METRICS_TIME_KEY + date + ":" + keyPrefix, String.valueOf(responseTime))
                .subscribe();

        recordVersionMetrics(serviceName, apiVersion, statDate, success, responseTime);

        if (clientVersion != null && !clientVersion.isEmpty()) {
            recordClientVersionMetrics(serviceName, apiVersion, clientVersion, userAgent, statDate, success);
        }

        log.debug("流量统计 - 路径: {}, 方法: {}, 版本: {}, 客户端版本: {}, 成功: {}, 耗时: {}ms",
                path, method, apiVersion, clientVersion, success, responseTime);
    }

    private void recordVersionMetrics(String serviceName, String apiVersion, String statDate,
                                      boolean success, long responseTime) {
        if (serviceName == null) {
            return;
        }

        String versionKey = METRICS_VERSION_KEY + serviceName + ":" + apiVersion;

        redisTemplate.opsForValue().get(versionKey)
                .defaultIfEmpty("{}")
                .flatMap(json -> {
                    try {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> stats = objectMapper.readValue(json, Map.class);
                        stats.put("serviceName", serviceName);
                        stats.put("version", apiVersion);
                        stats.put("statDate", statDate);
                        stats.put("callCount", ((Number) stats.getOrDefault("callCount", 0)).longValue() + 1);
                        stats.put("successCount", ((Number) stats.getOrDefault("successCount", 0)).longValue() + (success ? 1 : 0));
                        stats.put("failCount", ((Number) stats.getOrDefault("failCount", 0)).longValue() + (success ? 0 : 1));

                        long totalTime = ((Number) stats.getOrDefault("totalResponseTime", 0)).longValue() + responseTime;
                        long totalCalls = ((Number) stats.get("callCount")).longValue();
                        stats.put("totalResponseTime", totalTime);
                        stats.put("avgResponseTime", totalCalls > 0 ? totalTime / totalCalls : 0);

                        String newJson = objectMapper.writeValueAsString(stats);
                        return redisTemplate.opsForValue().set(versionKey, newJson, 48, TimeUnit.HOURS);
                    } catch (Exception e) {
                        log.warn("更新版本统计失败: {}", e.getMessage());
                        return Mono.empty();
                    }
                })
                .subscribe();
    }

    private void recordClientVersionMetrics(String serviceName, String apiVersion, String clientVersion,
                                            String userAgent, String statDate, boolean success) {
        if (serviceName == null) {
            return;
        }

        String clientKey = METRICS_CLIENT_KEY + serviceName + ":" + apiVersion + ":" + clientVersion;

        redisTemplate.opsForValue().get(clientKey)
                .defaultIfEmpty("{}")
                .flatMap(json -> {
                    try {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> stats = objectMapper.readValue(json, Map.class);
                        stats.put("serviceName", serviceName);
                        stats.put("apiVersion", apiVersion);
                        stats.put("clientVersion", clientVersion);
                        stats.put("userAgent", userAgent);
                        stats.put("statDate", statDate);
                        stats.put("callCount", ((Number) stats.getOrDefault("callCount", 0)).longValue() + 1);
                        stats.put("successCount", ((Number) stats.getOrDefault("successCount", 0)).longValue() + (success ? 1 : 0));
                        stats.put("failCount", ((Number) stats.getOrDefault("failCount", 0)).longValue() + (success ? 0 : 1));

                        String newJson = objectMapper.writeValueAsString(stats);
                        return redisTemplate.opsForValue().set(clientKey, newJson, 48, TimeUnit.HOURS);
                    } catch (Exception e) {
                        log.warn("更新客户端版本统计失败: {}", e.getMessage());
                        return Mono.empty();
                    }
                })
                .subscribe();
    }

    private String extractServiceName(String path) {
        String[] parts = path.split("/");
        if (parts.length >= 3 && "api".equals(parts[1])) {
            return parts[2];
        }
        return null;
    }

    @Override
    public int getOrder() {
        return -80;
    }
}

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
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class MockResponseFilter implements GlobalFilter, Ordered {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String VERSION_HEADER = "X-API-Version";
    private static final String MOCK_CONFIG_KEY_PREFIX = "api:mock:config:";
    private static final String MOCK_RESPONSE_HEADER = "X-Mock-Response";
    private static final String MOCK_TYPE_HEADER = "X-Mock-Type";
    private static final String MOCK_DELAY_HEADER = "X-Mock-Delay";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String method = request.getMethod().name();
        String apiVersion = request.getHeaders().getFirst(VERSION_HEADER);

        if (apiVersion == null) {
            apiVersion = "v1";
        }

        String serviceName = extractServiceName(path);
        if (serviceName == null) {
            return chain.filter(exchange);
        }

        String finalApiVersion = apiVersion;
        return getMockConfig(serviceName, apiVersion, path, method)
                .flatMap(mockConfig -> {
                    if (mockConfig == null) {
                        return chain.filter(exchange);
                    }

                    log.info("Mock响应拦截: path={}, method={}, version={}, type={}",
                            path, method, finalApiVersion, mockConfig.getMockType());

                    return handleMockResponse(exchange, mockConfig);
                })
                .switchIfEmpty(chain.filter(exchange));
    }

    private Mono<MockConfig> getMockConfig(String serviceName, String version, String path, String method) {
        String versionKey = MOCK_CONFIG_KEY_PREFIX + "version:" + serviceName + ":" + version + ":" + method + ":" + path;
        String pathKey = MOCK_CONFIG_KEY_PREFIX + "path:" + method + ":" + path;

        return redisTemplate.opsForValue().get(versionKey)
                .switchIfEmpty(redisTemplate.opsForValue().get(pathKey))
                .map(json -> {
                    try {
                        return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
                    } catch (Exception e) {
                        log.warn("解析Mock配置失败: {}", e.getMessage());
                        return null;
                    }
                })
                .map(map -> {
                    if (map == null) return null;
                    MockConfig config = new MockConfig();
                    config.setMockType((String) map.get("mockType"));
                    config.setDelayMs(map.get("delayMs") != null ? ((Number) map.get("delayMs")).intValue() : 0);
                    config.setErrorCode(map.get("errorCode") != null ? ((Number) map.get("errorCode")).intValue() : 200);
                    config.setErrorMessage((String) map.get("errorMessage"));
                    config.setCustomResponse((String) map.get("customResponse"));
                    config.setServiceName((String) map.get("serviceName"));
                    config.setApiVersion((String) map.get("apiVersion"));
                    config.setPath((String) map.get("path"));
                    config.setMethod((String) map.get("method"));
                    return config;
                })
                .defaultIfEmpty(null);
    }

    private Mono<Void> handleMockResponse(ServerWebExchange exchange, MockConfig mockConfig) {
        ServerHttpResponse response = exchange.getResponse();

        response.getHeaders().add(MOCK_RESPONSE_HEADER, "true");
        response.getHeaders().add(MOCK_TYPE_HEADER, mockConfig.getMockType());
        response.getHeaders().add(MOCK_DELAY_HEADER, String.valueOf(mockConfig.getDelayMs()));

        Duration delay = Duration.ofMillis(mockConfig.getDelayMs());

        return Mono.delay(delay)
                .then(Mono.fromRunnable(() -> {
                    if ("DELAY".equals(mockConfig.getMockType())) {
                        response.setStatusCode(HttpStatus.OK);
                        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    } else if ("ERROR".equals(mockConfig.getMockType())) {
                        response.setStatusCode(HttpStatus.valueOf(mockConfig.getErrorCode()));
                        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    } else if ("CUSTOM".equals(mockConfig.getMockType())) {
                        response.setStatusCode(HttpStatus.valueOf(mockConfig.getErrorCode()));
                        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    } else {
                        response.setStatusCode(HttpStatus.OK);
                        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    }
                }))
                .then(Mono.defer(() -> {
                    String responseBody = buildMockResponseBody(mockConfig);
                    byte[] bytes = responseBody.getBytes(StandardCharsets.UTF_8);
                    DataBuffer buffer = response.bufferFactory().wrap(bytes);
                    return response.writeWith(Mono.just(buffer));
                }));
    }

    private String buildMockResponseBody(MockConfig mockConfig) {
        try {
            if ("CUSTOM".equals(mockConfig.getMockType()) && mockConfig.getCustomResponse() != null) {
                return mockConfig.getCustomResponse();
            }

            if ("ERROR".equals(mockConfig.getMockType())) {
                Map<String, Object> errorBody = new HashMap<>();
                errorBody.put("code", mockConfig.getErrorCode());
                errorBody.put("message", mockConfig.getErrorMessage() != null ?
                        mockConfig.getErrorMessage() : "Mock模拟错误");
                errorBody.put("mock", true);
                errorBody.put("mockType", mockConfig.getMockType());
                errorBody.put("service", mockConfig.getServiceName());
                errorBody.put("version", mockConfig.getApiVersion());
                errorBody.put("path", mockConfig.getPath());
                return objectMapper.writeValueAsString(errorBody);
            }

            if ("DELAY".equals(mockConfig.getMockType()) && mockConfig.getCustomResponse() != null) {
                return mockConfig.getCustomResponse();
            }

            if ("SUCCESS".equals(mockConfig.getMockType()) && mockConfig.getCustomResponse() != null) {
                return mockConfig.getCustomResponse();
            }

            Map<String, Object> defaultBody = new HashMap<>();
            defaultBody.put("code", mockConfig.getErrorCode());
            defaultBody.put("message", "Mock响应");
            defaultBody.put("mock", true);
            defaultBody.put("mockType", mockConfig.getMockType());
            defaultBody.put("delayMs", mockConfig.getDelayMs());
            defaultBody.put("service", mockConfig.getServiceName());
            defaultBody.put("version", mockConfig.getApiVersion());
            defaultBody.put("path", mockConfig.getPath());
            defaultBody.put("method", mockConfig.getMethod());
            defaultBody.put("timestamp", System.currentTimeMillis());
            defaultBody.put("data", new HashMap<String, Object>() {{
                put("mockData", true);
                put("exampleField", "mockValue");
            }});
            return objectMapper.writeValueAsString(defaultBody);

        } catch (Exception e) {
            log.error("构建Mock响应失败", e);
            return "{\"code\":500,\"message\":\"Mock响应构建失败\",\"mock\":true}";
        }
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
        return -85;
    }

    @lombok.Data
    public static class MockConfig {
        private String serviceName;
        private String apiVersion;
        private String path;
        private String method;
        private String mockType;
        private Integer delayMs;
        private Integer errorCode;
        private String errorMessage;
        private String customResponse;
    }
}

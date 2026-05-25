package com.apigateway.core.cache;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.PathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

/**
 * GET请求缓存全局过滤器
 * 缓存GET请求的响应结果，支持基于配置的缓存规则
 * 基于URL和查询参数生成缓存Key，支持细粒度的缓存策略配置
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RequestCacheFilter implements GlobalFilter, Ordered {

    /**
     * Redis缓存服务
     */
    private final RedisCacheService redisCacheService;

    /**
     * 缓存配置属性
     */
    private final CacheProperties cacheProperties;

    /**
     * 路径匹配器
     */
    private final PathMatcher pathMatcher = new AntPathMatcher();

    /**
     * 响应数据缓冲区工厂
     */
    private final DataBufferFactory dataBufferFactory = new DefaultDataBufferFactory();

    /**
     * 缓存数据的内容类型
     */
    private static final String CACHE_CONTENT_TYPE = "application/json";

    /**
     * 缓存响应头标识
     */
    private static final String CACHE_HIT_HEADER = "X-Cache-Hit";

    /**
     * 缓存名称
     */
    private static final String REQUEST_CACHE_NAME = "requestCache";

    /**
     * 过滤器执行顺序
     * 在认证过滤器之后，路由过滤器之前执行
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 200;
    }

    /**
     * 执行缓存过滤逻辑
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();

        if (!shouldCache(request)) {
            log.debug("不缓存请求 - method: {}, path: {}", request.getMethod(), request.getPath());
            return chain.filter(exchange);
        }

        String cacheKey = generateCacheKey(request);
        CacheProperties.CacheRule cacheRule = getCacheRule(request.getPath().value());
        Duration expireTime = getExpireTime(cacheRule);

        log.debug("尝试从缓存获取 - key: {}, path: {}", cacheKey, request.getPath());

        return redisCacheService.<CachedResponse>get(REQUEST_CACHE_NAME, cacheKey)
                .flatMap(cachedResponse -> {
                    log.debug("缓存命中 - key: {}", cacheKey);
                    return writeCachedResponse(exchange, cachedResponse);
                })
                .switchIfEmpty(Mono.defer(() -> {
                    log.debug("缓存未命中 - key: {}, 继续执行请求", cacheKey);
                    return chain.filter(exchange.mutate()
                            .response(cacheResponseDecorator(exchange, cacheKey, expireTime))
                            .build());
                }));
    }

    /**
     * 判断是否应该缓存该请求
     *
     * @param request HTTP请求
     * @return 是否缓存
     */
    private boolean shouldCache(ServerHttpRequest request) {
        if (!cacheProperties.isEnabled() || !cacheProperties.isCacheGetRequests()) {
            return false;
        }

        if (!HttpMethod.GET.equals(request.getMethod())) {
            return false;
        }

        String path = request.getPath().value();

        if (isExcludedPath(path)) {
            return false;
        }

        CacheProperties.CacheRule cacheRule = getCacheRule(path);
        return cacheRule == null || cacheRule.isEnabled();
    }

    /**
     * 判断路径是否在排除列表中
     *
     * @param path 请求路径
     * @return 是否排除
     */
    private boolean isExcludedPath(String path) {
        return cacheProperties.getExcludePaths().stream()
                .anyMatch(pattern -> pathMatcher.match(pattern, path));
    }

    /**
     * 获取匹配的缓存规则
     *
     * @param path 请求路径
     * @return 匹配的缓存规则，没有匹配返回null
     */
    private CacheProperties.CacheRule getCacheRule(String path) {
        return cacheProperties.getRules().stream()
                .filter(rule -> pathMatcher.match(rule.getPathPattern(), path))
                .findFirst()
                .orElse(null);
    }

    /**
     * 获取缓存过期时间
     *
     * @param cacheRule 缓存规则
     * @return 过期时间
     */
    private Duration getExpireTime(CacheProperties.CacheRule cacheRule) {
        if (cacheRule != null && cacheRule.getExpireTime() != null) {
            return cacheRule.getExpireTime();
        }
        return cacheProperties.getDefaultExpireTime();
    }

    /**
     * 生成缓存Key
     * 基于URL路径和查询参数生成，支持规则配置
     *
     * @param request HTTP请求
     * @return 缓存Key
     */
    private String generateCacheKey(ServerHttpRequest request) {
        String path = request.getPath().value();
        CacheProperties.CacheRule cacheRule = getCacheRule(path);

        Map<String, String> queryParams = filterQueryParams(request.getQueryParams().toSingleValueMap(), cacheRule);
        Map<String, String> headers = filterHeaders(request.getHeaders().toSingleValueMap(), cacheRule);

        StringBuilder keyBuilder = new StringBuilder();
        keyBuilder.append("GET:").append(path);

        if (!queryParams.isEmpty()) {
            keyBuilder.append(":params:");
            keyBuilder.append(queryParams.entrySet().stream()
                    .map(e -> e.getKey() + "=" + e.getValue())
                    .collect(Collectors.joining("&")));
        }

        if (!headers.isEmpty()) {
            keyBuilder.append(":headers:");
            keyBuilder.append(headers.entrySet().stream()
                    .map(e -> e.getKey() + "=" + e.getValue())
                    .collect(Collectors.joining("&")));
        }

        return keyBuilder.toString();
    }

    /**
     * 根据缓存规则过滤查询参数
     *
     * @param queryParams 原始查询参数
     * @param cacheRule   缓存规则
     * @return 过滤后的查询参数
     */
    private Map<String, String> filterQueryParams(Map<String, String> queryParams, CacheProperties.CacheRule cacheRule) {
        Map<String, String> sortedParams = new TreeMap<>(queryParams);

        if (cacheRule == null) {
            return sortedParams;
        }

        List<String> excludeParams = cacheRule.getExcludeQueryParams();
        if (excludeParams != null && !excludeParams.isEmpty()) {
            sortedParams.keySet().removeAll(excludeParams);
        }

        List<String> includeParams = cacheRule.getIncludeQueryParams();
        if (includeParams != null && !includeParams.isEmpty()) {
            sortedParams.keySet().retainAll(includeParams);
        }

        return sortedParams;
    }

    /**
     * 根据缓存规则过滤请求头
     *
     * @param headers   原始请求头
     * @param cacheRule 缓存规则
     * @return 过滤后的请求头
     */
    private Map<String, String> filterHeaders(Map<String, String> headers, CacheProperties.CacheRule cacheRule) {
        if (cacheRule == null || !cacheRule.isIncludeHeaders()) {
            return new TreeMap<>();
        }

        Map<String, String> sortedHeaders = new TreeMap<>(headers);
        List<String> includeHeaders = cacheRule.getIncludeHeadersList();

        if (includeHeaders != null && !includeHeaders.isEmpty()) {
            sortedHeaders.keySet().retainAll(includeHeaders);
        }

        return sortedHeaders;
    }

    /**
     * 写入缓存响应
     *
     * @param exchange       服务器Web交换对象
     * @param cachedResponse 缓存的响应
     * @return 响应式处理结果
     */
    private Mono<Void> writeCachedResponse(ServerWebExchange exchange, CachedResponse cachedResponse) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.valueOf(cachedResponse.getStatusCode()));
        response.getHeaders().addAll(cachedResponse.getHeaders());
        response.getHeaders().add(CACHE_HIT_HEADER, "true");
        response.getHeaders().setContentType(MediaType.parseMediaType(CACHE_CONTENT_TYPE));

        byte[] bodyBytes = cachedResponse.getBody().getBytes(StandardCharsets.UTF_8);
        DataBuffer buffer = dataBufferFactory.allocateBuffer(bodyBytes.length);
        buffer.write(bodyBytes);

        return response.writeWith(Flux.just(buffer));
    }

    /**
     * 创建响应装饰器，用于捕获响应并缓存
     *
     * @param exchange   服务器Web交换对象
     * @param cacheKey   缓存Key
     * @param expireTime 过期时间
     * @return 装饰后的响应
     */
    private ServerHttpResponseDecorator cacheResponseDecorator(ServerWebExchange exchange,
                                                               String cacheKey,
                                                               Duration expireTime) {
        return new ServerHttpResponseDecorator(exchange.getResponse()) {
            @Override
            public Mono<Void> writeWith(org.reactivestreams.Publisher<? extends DataBuffer> body) {
                if (getDelegate().getStatusCode() != null &&
                        getDelegate().getStatusCode().is2xxSuccessful()) {
                    return super.writeWith(DataBufferUtils.join(body)
                            .flatMap(dataBuffer -> {
                                byte[] bytes = new byte[dataBuffer.readableByteCount()];
                                dataBuffer.read(bytes);
                                String bodyString = new String(bytes, StandardCharsets.UTF_8);

                                CachedResponse cachedResponse = new CachedResponse(
                                        getDelegate().getStatusCode().value(),
                                        getDelegate().getHeaders().toSingleValueMap(),
                                        bodyString
                                );

                                redisCacheService.put(REQUEST_CACHE_NAME, cacheKey, cachedResponse, expireTime)
                                        .subscribe(null,
                                                error -> log.error("缓存响应失败 - key: {}, error: {}",
                                                        cacheKey, error.getMessage()));

                                getDelegate().getHeaders().add(CACHE_HIT_HEADER, "false");
                                DataBuffer buffer = dataBufferFactory.allocateBuffer(bytes.length);
                                buffer.write(bytes);
                                return Mono.just(buffer);
                            }));
                }
                return super.writeWith(body);
            }
        };
    }

    /**
     * 缓存响应内部类
     * 用于序列化存储响应数据
     */
    @lombok.Data
    @lombok.AllArgsConstructor
    @lombok.NoArgsConstructor
    public static class CachedResponse {
        /**
         * HTTP状态码
         */
        private int statusCode;

        /**
         * 响应头
         */
        private Map<String, String> headers;

        /**
         * 响应体
         */
        private String body;
    }

    /**
     * DataBuffer工具类
     */
    private static class DataBufferUtils {
        /**
         * 合并多个DataBuffer为一个
         *
         * @param buffers DataBuffer流
         * @return 合并后的DataBuffer
         */
        static Mono<DataBuffer> join(org.reactivestreams.Publisher<? extends DataBuffer> buffers) {
            return Flux.from(buffers)
                    .collect(() -> new java.io.ByteArrayOutputStream(),
                            (baos, buffer) -> {
                                byte[] bytes = new byte[buffer.readableByteCount()];
                                buffer.read(bytes);
                                try {
                                    baos.write(bytes);
                                } catch (java.io.IOException e) {
                                    throw new RuntimeException("读取响应体失败", e);
                                }
                            })
                    .map(baos -> {
                        byte[] bytes = baos.toByteArray();
                        DataBufferFactory factory = new DefaultDataBufferFactory();
                        DataBuffer buffer = factory.allocateBuffer(bytes.length);
                        buffer.write(bytes);
                        return buffer;
                    });
        }
    }
}

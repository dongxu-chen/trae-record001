package com.apigateway.core.replay;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import org.springframework.http.HttpMethod;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 全局请求录制过滤器
 * 实现GlobalFilter接口，录制符合条件的请求（方法、URL、Header、Body、时间戳）到Redis
 * 采用响应式编程风格，不阻塞请求处理流程
 * 使用请求装饰器模式实现请求体的多次读取
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RequestReplayFilter implements GlobalFilter, Ordered {

    /**
     * 请求重放服务
     */
    private final RequestReplayService requestReplayService;

    /**
     * 重放配置属性
     */
    private final ReplayProperties replayProperties;

    /**
     * 数据缓冲区工厂
     */
    private final DataBufferFactory dataBufferFactory = new DefaultDataBufferFactory();

    /**
     * 请求属性名称，用于存储录制的请求ID
     */
    private static final String REQUEST_ID_ATTR = "replayRequestId";

    /**
     * 请求开始时间属性名称
     */
    private static final String START_TIME_ATTR = "replayStartTime";

    /**
     * 过滤器执行顺序
     * 在日志过滤器之后，认证过滤器之前执行
     */
    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 100;
    }

    /**
     * 执行过滤器逻辑
     * 在请求进入时录制请求信息，在响应返回时更新响应状态码和耗时
     *
     * @param exchange 服务器Web交换对象，包含请求和响应信息
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!replayProperties.isEnabled()) {
            return chain.filter(exchange);
        }

        ServerHttpRequest request = exchange.getRequest();
        String method = request.getMethod().name();
        String path = request.getPath().value();

        if (!requestReplayService.shouldRecord(method, path)) {
            log.debug("请求不符合录制条件，跳过 - method: {}, path: {}", method, path);
            return chain.filter(exchange);
        }

        String requestId = UUID.randomUUID().toString();
        Instant startTime = Instant.now();

        exchange.getAttributes().put(REQUEST_ID_ATTR, requestId);
        exchange.getAttributes().put(START_TIME_ATTR, startTime);

        log.debug("开始录制请求 - requestId: {}, method: {}, path: {}", requestId, method, path);

        if (isBodyAllowed(method)) {
            return recordWithBody(exchange, chain, requestId, startTime);
        } else {
            return recordWithoutBody(exchange, chain, requestId, startTime);
        }
    }

    /**
     * 判断是否允许读取请求体
     * GET、HEAD、OPTIONS等方法不包含请求体
     *
     * @param method HTTP方法
     * @return 是否允许读取请求体
     */
    private boolean isBodyAllowed(String method) {
        return HttpMethod.POST.matches(method)
                || HttpMethod.PUT.matches(method)
                || HttpMethod.PATCH.matches(method)
                || HttpMethod.DELETE.matches(method);
    }

    /**
     * 录制带请求体的请求
     *
     * @param exchange  服务器Web交换对象
     * @param chain     过滤器链
     * @param requestId 请求ID
     * @param startTime 开始时间
     * @return 响应式处理结果
     */
    private Mono<Void> recordWithBody(ServerWebExchange exchange, GatewayFilterChain chain,
                                      String requestId, Instant startTime) {
        ServerHttpRequest request = exchange.getRequest();

        return DataBufferUtils.join(request.getBody())
                .defaultIfEmpty(dataBufferFactory.allocateBuffer(0))
                .flatMap(dataBuffer -> {
                    String body = "";
                    if (dataBuffer.readableByteCount() > 0) {
                        byte[] bytes = new byte[dataBuffer.readableByteCount()];
                        dataBuffer.read(bytes);
                        body = new String(bytes, StandardCharsets.UTF_8);

                        if (body.length() > replayProperties.getMaxBodySize()) {
                            body = body.substring(0, replayProperties.getMaxBodySize()) + "...[truncated]";
                            log.debug("请求体超过最大大小，已截断 - requestId: {}, originalSize: {}, maxSize: {}",
                                    requestId, body.length(), replayProperties.getMaxBodySize());
                        }
                    }

                    DataBuffer cachedBuffer = dataBufferFactory.allocateBuffer(body.getBytes(StandardCharsets.UTF_8).length);
                    cachedBuffer.write(body.getBytes(StandardCharsets.UTF_8));

                    ServerHttpRequest decoratedRequest = new ServerHttpRequestDecorator(request) {
                        @Override
                        public Flux<DataBuffer> getBody() {
                            return Flux.just(cachedBuffer);
                        }
                    };

                    RecordedRequest recordedRequest = buildRecordedRequest(exchange, requestId, startTime, body);
                    requestReplayService.recordRequest(recordedRequest)
                            .subscribe(null, e -> log.error("录制请求失败 - requestId: {}, error: {}",
                                    requestId, e.getMessage()));

                    return chain.filter(exchange.mutate().request(decoratedRequest).build())
                            .then(Mono.fromRunnable(() -> updateResponseStatus(exchange, requestId, startTime)));
                });
    }

    /**
     * 录制不带请求体的请求
     *
     * @param exchange  服务器Web交换对象
     * @param chain     过滤器链
     * @param requestId 请求ID
     * @param startTime 开始时间
     * @return 响应式处理结果
     */
    private Mono<Void> recordWithoutBody(ServerWebExchange exchange, GatewayFilterChain chain,
                                         String requestId, Instant startTime) {
        RecordedRequest recordedRequest = buildRecordedRequest(exchange, requestId, startTime, null);
        requestReplayService.recordRequest(recordedRequest)
                .subscribe(null, e -> log.error("录制请求失败 - requestId: {}, error: {}",
                        requestId, e.getMessage()));

        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> updateResponseStatus(exchange, requestId, startTime)));
    }

    /**
     * 构建录制请求对象
     *
     * @param exchange  服务器Web交换对象
     * @param requestId 请求ID
     * @param startTime 开始时间
     * @param body      请求体
     * @return 录制请求对象
     */
    private RecordedRequest buildRecordedRequest(ServerWebExchange exchange, String requestId,
                                                 Instant startTime, String body) {
        ServerHttpRequest request = exchange.getRequest();

        Map<String, String> headers = new HashMap<>();
        if (replayProperties.isRecordHeaders()) {
            List<String> excludeHeaders = replayProperties.getExcludeHeaders();
            request.getHeaders().forEach((key, values) -> {
                if (!excludeHeaders.contains(key)) {
                    headers.put(key, String.join(",", values));
                }
            });
        }

        Map<String, String[]> queryParams = new HashMap<>();
        request.getQueryParams().forEach((key, values) ->
                queryParams.put(key, values.toArray(new String[0])));

        String clientIp = request.getRemoteAddress() != null
                ? request.getRemoteAddress().getAddress().getHostAddress()
                : "unknown";

        return RecordedRequest.builder()
                .requestId(requestId)
                .method(request.getMethod().name())
                .url(request.getURI().toString())
                .path(request.getPath().value())
                .queryParams(queryParams)
                .headers(headers)
                .body(body)
                .timestamp(startTime)
                .clientIp(clientIp)
                .build();
    }

    /**
     * 更新响应状态码和耗时
     *
     * @param exchange  服务器Web交换对象
     * @param requestId 请求ID
     * @param startTime 开始时间
     */
    private void updateResponseStatus(ServerWebExchange exchange, String requestId, Instant startTime) {
        ServerHttpResponse response = exchange.getResponse();
        Integer statusCode = response.getStatusCode() != null
                ? response.getStatusCode().value()
                : null;

        long duration = java.time.Duration.between(startTime, Instant.now()).toMillis();

        requestReplayService.getRecordedRequest(requestId)
                .flatMap(recordedRequest -> {
                    recordedRequest.setResponseStatus(statusCode);
                    recordedRequest.setDuration(duration);
                    return requestReplayService.recordRequest(recordedRequest);
                })
                .subscribe(null, e -> log.debug("更新请求响应状态失败 - requestId: {}, error: {}",
                        requestId, e.getMessage()));
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
                                    throw new RuntimeException("读取请求体失败", e);
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

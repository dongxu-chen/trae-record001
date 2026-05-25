package com.apigateway.core.resilience4j;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.resilience4j.bulkhead.BulkheadFullException;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import io.github.resilience4j.timelimiter.TimeoutException;
import lombok.Builder;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * 降级处理器
 * 提供不同服务的降级返回逻辑
 * 统一返回JSON格式的错误响应
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class FallbackHandler {

    private static final DateTimeFormatter DATE_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final ObjectMapper objectMapper;

    /**
     * 处理降级逻辑
     * 根据异常类型和服务类型返回不同的降级响应
     *
     * @param exchange   服务器交换对象
     * @param serviceKey 服务标识
     * @param throwable  异常对象
     * @return 响应式Mono对象
     */
    public Mono<Void> handleFallback(ServerWebExchange exchange, String serviceKey, Throwable throwable) {
        FallbackResponse fallbackResponse = buildFallbackResponse(serviceKey, throwable);
        HttpStatus httpStatus = resolveHttpStatus(throwable);

        log.warn("服务降级触发 - 服务: {}, 状态码: {}, 异常类型: {}, 消息: {}",
                serviceKey, httpStatus.value(), throwable.getClass().getSimpleName(), throwable.getMessage());

        return writeErrorResponse(exchange, fallbackResponse, httpStatus);
    }

    /**
     * 构建降级响应对象
     * 根据异常类型和服务类型构建合适的响应信息
     *
     * @param serviceKey 服务标识
     * @param throwable  异常对象
     * @return 降级响应对象
     */
    private FallbackResponse buildFallbackResponse(String serviceKey, Throwable throwable) {
        String errorCode;
        String errorMessage;
        String suggestion;

        if (throwable instanceof CallNotPermittedException) {
            errorCode = "CIRCUIT_BREAKER_OPEN";
            errorMessage = String.format("服务 %s 已熔断，请稍后重试", getServiceName(serviceKey));
            suggestion = "请检查服务状态，或稍后再试";
        } else if (throwable instanceof RequestNotPermitted) {
            errorCode = "RATE_LIMIT_EXCEEDED";
            errorMessage = String.format("服务 %s 请求频率超限，请稍后重试", getServiceName(serviceKey));
            suggestion = "请降低请求频率，或联系管理员提升限流阈值";
        } else if (throwable instanceof TimeoutException) {
            errorCode = "SERVICE_TIMEOUT";
            errorMessage = String.format("服务 %s 请求超时，请稍后重试", getServiceName(serviceKey));
            suggestion = "请检查网络连接，或稍后再试";
        } else if (throwable instanceof BulkheadFullException) {
            errorCode = "BULKHEAD_FULL";
            errorMessage = String.format("服务 %s 并发请求已满，请稍后重试", getServiceName(serviceKey));
            suggestion = "请稍后再试，或联系管理员提升并发限制";
        } else {
            errorCode = "SERVICE_ERROR";
            errorMessage = String.format("服务 %s 发生异常，请稍后重试", getServiceName(serviceKey));
            suggestion = "请稍后再试，如问题持续请联系管理员";
        }

        return FallbackResponse.builder()
                .success(false)
                .code(errorCode)
                .message(errorMessage)
                .suggestion(suggestion)
                .service(getServiceName(serviceKey))
                .timestamp(LocalDateTime.now().format(DATE_TIME_FORMATTER))
                .data(Map.of())
                .build();
    }

    /**
     * 根据异常类型解析HTTP状态码
     *
     * @param throwable 异常对象
     * @return HTTP状态码
     */
    private HttpStatus resolveHttpStatus(Throwable throwable) {
        if (throwable instanceof CallNotPermittedException) {
            return HttpStatus.SERVICE_UNAVAILABLE;
        } else if (throwable instanceof RequestNotPermitted) {
            return HttpStatus.TOO_MANY_REQUESTS;
        } else if (throwable instanceof TimeoutException) {
            return HttpStatus.GATEWAY_TIMEOUT;
        } else if (throwable instanceof BulkheadFullException) {
            return HttpStatus.SERVICE_UNAVAILABLE;
        } else {
            return HttpStatus.INTERNAL_SERVER_ERROR;
        }
    }

    /**
     * 获取服务名称
     * 将服务标识转换为友好的服务名称
     *
     * @param serviceKey 服务标识
     * @return 服务名称
     */
    private String getServiceName(String serviceKey) {
        return switch (serviceKey) {
            case "restService" -> "REST API服务";
            case "grpcService" -> "gRPC服务";
            case "graphqlService" -> "GraphQL服务";
            case "aggregateService" -> "聚合服务";
            default -> "网关服务";
        };
    }

    /**
     * 写入错误响应
     * 将降级响应以JSON格式写入响应体
     *
     * @param exchange         服务器交换对象
     * @param fallbackResponse 降级响应对象
     * @param httpStatus       HTTP状态码
     * @return 响应式Mono对象
     */
    private Mono<Void> writeErrorResponse(ServerWebExchange exchange, FallbackResponse fallbackResponse, HttpStatus httpStatus) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(httpStatus);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);

        try {
            String jsonResponse = objectMapper.writeValueAsString(fallbackResponse);
            byte[] bytes = jsonResponse.getBytes(StandardCharsets.UTF_8);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            return response.writeWith(Mono.just(buffer));
        } catch (Exception e) {
            log.error("序列化降级响应失败", e);
            String errorJson = String.format("{\"success\":false,\"code\":\"SERIALIZATION_ERROR\",\"message\":\"%s\"}",
                    e.getMessage());
            byte[] bytes = errorJson.getBytes(StandardCharsets.UTF_8);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            return response.writeWith(Mono.just(buffer));
        }
    }

    /**
     * 降级响应对象
     * 定义统一的错误响应格式
     */
    @Data
    @Builder
    public static class FallbackResponse {
        /**
         * 请求是否成功
         */
        private boolean success;

        /**
         * 错误码
         */
        private String code;

        /**
         * 错误消息
         */
        private String message;

        /**
         * 建议
         */
        private String suggestion;

        /**
         * 服务名称
         */
        private String service;

        /**
         * 时间戳
         */
        private String timestamp;

        /**
         * 数据字段，默认为空Map
         */
        private Map<String, Object> data;
    }
}

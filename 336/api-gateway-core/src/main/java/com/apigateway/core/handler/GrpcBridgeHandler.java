package com.apigateway.core.handler;

import com.apigateway.grpc.bridge.GrpcBridgeService;
import com.apigateway.grpc.order.CreateOrderRequest;
import com.apigateway.grpc.order.GetOrderRequest;
import com.apigateway.grpc.order.ListOrdersRequest;
import com.apigateway.grpc.order.OrderResponse;
import com.apigateway.grpc.order.UpdateOrderStatusRequest;
import com.apigateway.grpc.user.CreateUserRequest;
import com.apigateway.grpc.user.DeleteUserRequest;
import com.apigateway.grpc.user.GetUserRequest;
import com.apigateway.grpc.user.ListUsersRequest;
import com.apigateway.grpc.user.UpdateUserRequest;
import com.apigateway.grpc.user.UserResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * gRPC桥接处理器
 * 处理/api/grpc/**请求，将HTTP请求转换为gRPC调用
 * 支持UserService和OrderService的各种方法调用
 * 使用Spring WebFlux函数式编程风格
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GrpcBridgeHandler {

    /**
     * gRPC桥接服务
     */
    private final GrpcBridgeService grpcBridgeService;

    /**
     * JSON对象映射器
     */
    private final ObjectMapper objectMapper;

    /**
     * 服务名常量
     */
    private static final String USER_SERVICE = "UserService";
    private static final String ORDER_SERVICE = "OrderService";

    /**
     * 处理gRPC请求
     * 根据路径中的服务名和方法名动态调用对应的gRPC服务
     * 支持元数据映射和Header超时传递
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> handleGrpcRequest(ServerRequest request) {
        String path = request.path();
        log.debug("收到gRPC桥接请求 - path: {}", path);

        String[] pathSegments = path.split("/");
        if (pathSegments.length < 4) {
            return badRequest("无效的请求路径，格式应为: /api/grpc/{service}/{method}");
        }

        String serviceName = pathSegments[2];
        String methodName = pathSegments[3];

        Map<String, String> headers = extractHeaders(request);
        Duration customTimeout = extractTimeoutFromHeader(request);

        log.debug("解析gRPC请求 - service: {}, method: {}, timeout: {}ms",
                serviceName, methodName, customTimeout != null ? customTimeout.toMillis() : "default");

        return request.bodyToMono(String.class)
                .defaultIfEmpty("{}")
                .flatMap(requestBody -> invokeGrpcServiceWithMetadata(
                        serviceName, methodName, requestBody, headers, customTimeout))
                .flatMap(grpcResponse -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .headers(httpHeaders -> addGrpcResponseHeaders(httpHeaders, grpcResponse.headers()))
                        .bodyValue(grpcResponse.response()))
                .onErrorResume(this::handleError);
    }

    /**
     * 调用gRPC服务（带元数据）
     *
     * @param serviceName   服务名
     * @param methodName    方法名
     * @param requestBody   请求体JSON
     * @param headers       请求头映射
     * @param customTimeout 自定义超时
     * @return gRPC响应Mono
     */
    private Mono<GrpcBridgeService.GrpcResponse> invokeGrpcServiceWithMetadata(
            String serviceName, String methodName, String requestBody,
            Map<String, String> headers, Duration customTimeout) {
        return switch (serviceName.toLowerCase()) {
            case "user", "userservice" -> invokeUserServiceWithMetadata(
                    methodName, requestBody, headers, customTimeout);
            case "order", "orderservice" -> invokeOrderServiceWithMetadata(
                    methodName, requestBody, headers, customTimeout);
            default -> Mono.error(new IllegalArgumentException("不支持的服务: " + serviceName));
        };
    }

    /**
     * 调用UserService（带元数据）
     *
     * @param methodName    方法名
     * @param requestBody   请求体JSON
     * @param headers       请求头映射
     * @param customTimeout 自定义超时
     * @return gRPC响应Mono
     */
    private Mono<GrpcBridgeService.GrpcResponse> invokeUserServiceWithMetadata(
            String methodName, String requestBody, Map<String, String> headers, Duration customTimeout) {
        return switch (methodName.toLowerCase()) {
            case "getuser", "get" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    USER_SERVICE, "GetUser", requestBody,
                    GetUserRequest.class, UserResponse.class, headers, customTimeout);
            case "listusers", "list" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    USER_SERVICE, "ListUsers", requestBody,
                    ListUsersRequest.class, com.apigateway.grpc.user.ListUsersResponse.class, headers, customTimeout);
            case "createuser", "create" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    USER_SERVICE, "CreateUser", requestBody,
                    CreateUserRequest.class, UserResponse.class, headers, customTimeout);
            case "updateuser", "update" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    USER_SERVICE, "UpdateUser", requestBody,
                    UpdateUserRequest.class, UserResponse.class, headers, customTimeout);
            case "deleteuser", "delete" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    USER_SERVICE, "DeleteUser", requestBody,
                    DeleteUserRequest.class, com.apigateway.grpc.user.DeleteUserResponse.class, headers, customTimeout);
            default -> Mono.error(new IllegalArgumentException(
                    "UserService不支持的方法: " + methodName));
        };
    }

    /**
     * 调用OrderService（带元数据）
     *
     * @param methodName    方法名
     * @param requestBody   请求体JSON
     * @param headers       请求头映射
     * @param customTimeout 自定义超时
     * @return gRPC响应Mono
     */
    private Mono<GrpcBridgeService.GrpcResponse> invokeOrderServiceWithMetadata(
            String methodName, String requestBody, Map<String, String> headers, Duration customTimeout) {
        return switch (methodName.toLowerCase()) {
            case "getorder", "get" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    ORDER_SERVICE, "GetOrder", requestBody,
                    GetOrderRequest.class, OrderResponse.class, headers, customTimeout);
            case "listorders", "list" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    ORDER_SERVICE, "ListOrders", requestBody,
                    ListOrdersRequest.class, com.apigateway.grpc.order.ListOrdersResponse.class, headers, customTimeout);
            case "createorder", "create" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    ORDER_SERVICE, "CreateOrder", requestBody,
                    CreateOrderRequest.class, OrderResponse.class, headers, customTimeout);
            case "updateorderstatus", "update", "updatestatus" -> grpcBridgeService.invokeGrpcMethodWithMetadata(
                    ORDER_SERVICE, "UpdateOrderStatus", requestBody,
                    UpdateOrderStatusRequest.class, OrderResponse.class, headers, customTimeout);
            default -> Mono.error(new IllegalArgumentException(
                    "OrderService不支持的方法: " + methodName));
        };
    }

    /**
     * 从请求中提取Header
     *
     * @param request 服务器请求
     * @return Header Map
     */
    private Map<String, String> extractHeaders(ServerRequest request) {
        Map<String, String> headers = new HashMap<>();
        HttpHeaders httpHeaders = request.headers().asHttpHeaders();
        httpHeaders.forEach((key, value) -> {
            if (key.toLowerCase().startsWith("x-grpc-")) {
                headers.put(key, value != null && !value.isEmpty() ? value.get(0) : "");
            }
        });
        log.debug("提取gRPC相关Header: {}", headers.keySet());
        return headers;
    }

    /**
     * 从Header中提取超时时间
     *
     * @param request 服务器请求
     * @return 超时时间Duration，如果没有则返回null
     */
    private Duration extractTimeoutFromHeader(ServerRequest request) {
        String timeoutHeader = request.headers().firstHeader("X-Grpc-Timeout");
        if (timeoutHeader != null && !timeoutHeader.isEmpty()) {
            try {
                long timeoutMs = Long.parseLong(timeoutHeader);
                return Duration.ofMillis(timeoutMs);
            } catch (NumberFormatException e) {
                log.warn("解析X-Grpc-Timeout失败: {}", timeoutHeader);
            }
        }
        return null;
    }

    /**
     * 将gRPC响应元数据添加到HTTP响应头
     *
     * @param httpHeaders HTTP响应头
     * @param grpcHeaders gRPC响应元数据
     */
    private void addGrpcResponseHeaders(HttpHeaders httpHeaders, Map<String, String> grpcHeaders) {
        if (grpcHeaders != null && !grpcHeaders.isEmpty()) {
            grpcHeaders.forEach(httpHeaders::set);
            log.debug("添加gRPC响应Header到HTTP响应: {}", grpcHeaders.keySet());
        }
    }

    /**
     * 快速获取用户信息
     * 支持通过查询参数传递用户ID
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> getUser(ServerRequest request) {
        String userId = request.queryParam("id")
                .orElse(request.pathVariable("id"));

        log.debug("快速获取用户信息 - userId: {}", userId);

        String requestBody = String.format("{\"id\": %s}", userId);
        return grpcBridgeService.invokeGrpcMethod(
                        USER_SERVICE, "GetUser", requestBody,
                        GetUserRequest.class, UserResponse.class)
                .flatMap(response -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(response))
                .onErrorResume(this::handleError);
    }

    /**
     * 快速获取订单信息
     * 支持通过查询参数传递订单ID
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> getOrder(ServerRequest request) {
        String orderId = request.queryParam("orderId")
                .orElse(request.pathVariable("orderId"));

        log.debug("快速获取订单信息 - orderId: {}", orderId);

        String requestBody = String.format("{\"orderId\": \"%s\"}", orderId);
        return grpcBridgeService.invokeGrpcMethod(
                        ORDER_SERVICE, "GetOrder", requestBody,
                        GetOrderRequest.class, OrderResponse.class)
                .flatMap(response -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(response))
                .onErrorResume(this::handleError);
    }

    /**
     * 检查gRPC服务健康状态
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> checkHealth(ServerRequest request) {
        String serviceName = request.queryParam("service")
                .orElse(USER_SERVICE);

        log.debug("检查gRPC服务健康状态 - service: {}", serviceName);

        return grpcBridgeService.checkServiceHealth(serviceName)
                .flatMap(healthy -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(Map.of(
                                "service", serviceName,
                                "healthy", healthy
                        )))
                .onErrorResume(this::handleError);
    }

    /**
     * 获取gRPC服务统计信息
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> getStats(ServerRequest request) {
        log.debug("获取gRPC服务统计信息");

        return grpcBridgeService.getActiveConnectionCount()
                .flatMap(count -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(Map.of(
                                "activeConnections", count,
                                "timestamp", System.currentTimeMillis()
                        )))
                .onErrorResume(this::handleError);
    }

    /**
     * 错误处理
     *
     * @param throwable 异常
     * @return 错误响应Mono
     */
    private Mono<ServerResponse> handleError(Throwable throwable) {
        log.error("gRPC桥接处理失败: {}", throwable.getMessage(), throwable);

        int statusCode = 500;
        String errorCode = "GRPC_BRIDGE_ERROR";
        String errorMessage = throwable.getMessage();

        if (throwable instanceof IllegalArgumentException) {
            statusCode = 400;
            errorCode = "INVALID_REQUEST";
        }

        Map<String, Object> errorBody = Map.of(
                "code", errorCode,
                "message", errorMessage,
                "success", false
        );

        return ServerResponse.status(statusCode)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(errorBody);
    }

    /**
     * 返回坏请求响应
     *
     * @param message 错误消息
     * @return 坏请求响应Mono
     */
    private Mono<ServerResponse> badRequest(String message) {
        log.warn("gRPC桥接坏请求: {}", message);

        Map<String, Object> errorBody = Map.of(
                "code", "BAD_REQUEST",
                "message", message,
                "success", false
        );

        return ServerResponse.badRequest()
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(errorBody);
    }
}

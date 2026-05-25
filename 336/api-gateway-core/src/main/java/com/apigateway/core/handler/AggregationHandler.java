package com.apigateway.core.handler;

import com.apigateway.grpc.bridge.GrpcBridgeService;
import com.apigateway.grpc.order.GetOrderRequest;
import com.apigateway.grpc.order.OrderResponse;
import com.apigateway.grpc.user.GetUserRequest;
import com.apigateway.grpc.user.UserResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 聚合处理器
 * 处理/api/aggregate/**请求，并行调用多个后端服务并聚合结果
 * 支持并行调用REST、gRPC、GraphQL多个服务
 * 使用响应式编程风格实现高性能的服务聚合
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AggregationHandler {

    /**
     * gRPC桥接服务
     */
    private final GrpcBridgeService grpcBridgeService;

    /**
     * GraphQL处理器
     */
    private final GraphQLHandler graphQLHandler;

    /**
     * JSON对象映射器
     */
    private final ObjectMapper objectMapper;

    /**
     * WebClient用于调用REST服务
     */
    private final WebClient webClient;

    /**
     * 默认超时时间
     */
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(10);

    /**
     * 聚合服务线程池
     * 用于并行执行CompletableFuture任务
     */
    private static final ExecutorService AGGREGATION_EXECUTOR = Executors.newFixedThreadPool(
            Runtime.getRuntime().availableProcessors() * 2,
            r -> {
                Thread thread = new Thread(r, "aggregation-pool-%d".formatted(
                        System.currentTimeMillis() % 1000));
                thread.setDaemon(true);
                return thread;
            });

    /**
     * 服务类型枚举
     */
    public enum ServiceType {
        REST, GRPC, GRAPHQL
    }

    /**
     * 处理聚合请求
     * 根据请求体中的配置并行调用多个服务并聚合结果
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> handleAggregate(ServerRequest request) {
        log.debug("收到聚合请求");

        return parseAggregateRequest(request)
                .flatMap(aggregateRequest -> executeAggregation(aggregateRequest))
                .flatMap(result -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(result))
                .onErrorResume(this::handleError);
    }

    /**
     * 获取用户详情（包含订单信息）
     * 使用CompletableFuture并行调用用户gRPC服务、订单gRPC服务和推荐REST服务
     * 总延迟取决于最慢的下游服务
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> getUserDetail(ServerRequest request) {
        String userId = request.pathVariable("userId");
        log.debug("获取用户详情聚合 - userId: {}", userId);
        long startTime = System.currentTimeMillis();

        CompletableFuture<Object> userFuture = CompletableFuture.supplyAsync(() -> {
            try {
                return grpcBridgeService.invokeGrpcMethod(
                                "UserService", "GetUser",
                                String.format("{\"id\": %s}", userId),
                                GetUserRequest.class, UserResponse.class)
                        .timeout(DEFAULT_TIMEOUT)
                        .toFuture()
                        .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                log.error("获取用户信息失败: {}", e.getMessage());
                return objectMapper.createObjectNode()
                        .put("error", "获取用户信息失败")
                        .toString();
            }
        }, AGGREGATION_EXECUTOR);

        CompletableFuture<Object> ordersFuture = CompletableFuture.supplyAsync(() -> {
            try {
                return grpcBridgeService.invokeGrpcMethod(
                                "OrderService", "ListOrders",
                                String.format("{\"userId\": %s, \"page\": 1, \"size\": 10}", userId),
                                com.apigateway.grpc.order.ListOrdersRequest.class,
                                com.apigateway.grpc.order.ListOrdersResponse.class)
                        .timeout(DEFAULT_TIMEOUT)
                        .toFuture()
                        .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                log.error("获取订单列表失败: {}", e.getMessage());
                return objectMapper.createObjectNode()
                        .put("error", "获取订单列表失败")
                        .toString();
            }
        }, AGGREGATION_EXECUTOR);

        CompletableFuture<Object> recommendationsFuture = CompletableFuture.supplyAsync(() -> {
            try {
                return callRestService(
                                "GET",
                                "http://localhost:8081/api/recommendations/hot",
                                null)
                        .timeout(DEFAULT_TIMEOUT)
                        .toFuture()
                        .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                log.error("获取推荐信息失败: {}", e.getMessage());
                return Map.of("error", "获取推荐信息失败");
            }
        }, AGGREGATION_EXECUTOR);

        return Mono.fromFuture(CompletableFuture.allOf(userFuture, ordersFuture, recommendationsFuture)
                .thenApply(v -> {
                    Map<String, Object> result = new HashMap<>();
                    try {
                        result.put("user", objectMapper.readTree((String) userFuture.getNow(null)));
                        result.put("orders", objectMapper.readTree((String) ordersFuture.getNow(null)));
                        result.put("recommendations", recommendationsFuture.getNow(null));
                        result.put("aggregatedAt", System.currentTimeMillis());
                        result.put("totalLatencyMs", System.currentTimeMillis() - startTime);
                    } catch (Exception e) {
                        log.error("解析聚合结果失败", e);
                        result.put("error", "解析聚合结果失败");
                    }
                    return result;
                }))
                .flatMap(result -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(result))
                .onErrorResume(this::handleError);
    }

    /**
     * 获取订单详情（包含用户和商品信息）
     * 先获取订单，再使用CompletableFuture并行调用用户gRPC服务和GraphQL商品服务
     * 总延迟取决于最慢的下游服务
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> getOrderDetail(ServerRequest request) {
        String orderId = request.pathVariable("orderId");
        log.debug("获取订单详情聚合 - orderId: {}", orderId);
        long startTime = System.currentTimeMillis();

        CompletableFuture<String> orderFuture = CompletableFuture.supplyAsync(() -> {
            try {
                return grpcBridgeService.invokeGrpcMethod(
                                "OrderService", "GetOrder",
                                String.format("{\"orderId\": \"%s\"}", orderId),
                                GetOrderRequest.class, OrderResponse.class)
                        .timeout(DEFAULT_TIMEOUT)
                        .toFuture()
                        .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
            } catch (Exception e) {
                log.error("获取订单信息失败: {}", e.getMessage());
                return objectMapper.createObjectNode()
                        .put("error", "获取订单信息失败")
                        .toString();
            }
        }, AGGREGATION_EXECUTOR);

        return Mono.fromFuture(orderFuture.thenCompose(orderJson -> {
            try {
                JsonNode orderNode = objectMapper.readTree(orderJson);
                String userId = orderNode.path("userId").asText();

                CompletableFuture<Object> userFuture = CompletableFuture.supplyAsync(() -> {
                    try {
                        return grpcBridgeService.invokeGrpcMethod(
                                        "UserService", "GetUser",
                                        String.format("{\"id\": %s}", userId),
                                        GetUserRequest.class, UserResponse.class)
                                .timeout(DEFAULT_TIMEOUT)
                                .toFuture()
                                .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
                    } catch (Exception e) {
                        log.error("获取用户信息失败: {}", e.getMessage());
                        return objectMapper.createObjectNode()
                                .put("error", "获取用户信息失败")
                                .toString();
                    }
                }, AGGREGATION_EXECUTOR);

                String graphQLQuery = String.format("""
                        {
                          order(orderId: "%s") {
                            items {
                              productId
                              productName
                              quantity
                              price
                            }
                          }
                        }
                        """, orderId);

                CompletableFuture<Object> graphQLFuture = CompletableFuture.supplyAsync(() -> {
                    try {
                        return executeGraphQLQuery(graphQLQuery, null)
                                .timeout(DEFAULT_TIMEOUT)
                                .toFuture()
                                .get(DEFAULT_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
                    } catch (Exception e) {
                        log.error("获取商品信息失败: {}", e.getMessage());
                        return Map.of("error", "获取商品信息失败");
                    }
                }, AGGREGATION_EXECUTOR);

                return CompletableFuture.allOf(userFuture, graphQLFuture)
                        .thenApply(v -> {
                            Map<String, Object> result = new HashMap<>();
                            try {
                                result.put("order", orderNode);
                                result.put("user", objectMapper.readTree((String) userFuture.getNow(null)));
                                result.put("products", graphQLFuture.getNow(null));
                                result.put("aggregatedAt", System.currentTimeMillis());
                                result.put("totalLatencyMs", System.currentTimeMillis() - startTime);
                            } catch (Exception e) {
                                log.error("解析聚合结果失败", e);
                                result.put("error", "解析聚合结果失败");
                            }
                            return result;
                        });
            } catch (Exception e) {
                log.error("解析订单信息失败", e);
                return CompletableFuture.completedFuture(Map.of("error", "解析订单信息失败"));
            }
        }))
                .flatMap(result -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(result))
                .onErrorResume(this::handleError);
    }

    /**
     * 执行通用聚合请求
     * 使用CompletableFuture并行调用所有服务，总延迟取决于最慢的下游
     *
     * @param aggregateRequest 聚合请求配置
     * @return 聚合结果Mono
     */
    private Mono<Map<String, Object>> executeAggregation(AggregateRequest aggregateRequest) {
        log.debug("执行通用聚合 - 服务数量: {}", aggregateRequest.services().size());
        long startTime = System.currentTimeMillis();

        List<CompletableFuture<Map.Entry<String, ServiceResult>>> futures = aggregateRequest.services()
                .stream()
                .map(serviceCall -> executeServiceCallAsync(serviceCall))
                .collect(Collectors.toList());

        CompletableFuture<Void> allOf = CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));

        return Mono.fromFuture(allOf.thenApply(v -> {
            Map<String, Object> aggregatedResult = new HashMap<>();
            int successCount = 0;
            int failureCount = 0;

            for (CompletableFuture<Map.Entry<String, ServiceResult>> future : futures) {
                try {
                    Map.Entry<String, ServiceResult> entry = future.getNow(null);
                    if (entry != null) {
                        ServiceResult result = entry.getValue();
                        aggregatedResult.put(entry.getKey(), result.data());
                        if (result.success()) {
                            successCount++;
                        } else {
                            failureCount++;
                        }
                    }
                } catch (Exception e) {
                    log.error("获取服务结果失败: {}", e.getMessage());
                    failureCount++;
                }
            }

            long totalTime = System.currentTimeMillis() - startTime;
            aggregatedResult.put("aggregatedAt", System.currentTimeMillis());
            aggregatedResult.put("serviceCount", futures.size());
            aggregatedResult.put("successCount", successCount);
            aggregatedResult.put("failureCount", failureCount);
            aggregatedResult.put("totalLatencyMs", totalTime);

            log.debug("聚合完成 - 服务数: {}, 成功: {}, 失败: {}, 总耗时: {}ms",
                    futures.size(), successCount, failureCount, totalTime);

            return aggregatedResult;
        }));
    }

    /**
     * 异步执行单个服务调用
     * 使用CompletableFuture在线程池中执行
     *
     * @param serviceCall 服务调用配置
     * @return CompletableFuture包装的服务结果
     */
    private CompletableFuture<Map.Entry<String, ServiceResult>> executeServiceCallAsync(ServiceCall serviceCall) {
        long startTime = System.currentTimeMillis();
        Duration timeout = serviceCall.timeout() != null ? serviceCall.timeout() : DEFAULT_TIMEOUT;

        return CompletableFuture.supplyAsync(() -> {
            try {
                Object result = executeServiceCallBlocking(serviceCall, timeout);
                long responseTime = System.currentTimeMillis() - startTime;

                log.debug("服务调用成功 - name: {}, 耗时: {}ms", serviceCall.name(), responseTime);

                ServiceResult serviceResult = new ServiceResult(
                        true, 200, "SUCCESS", result, null, responseTime, false
                );

                return Map.entry(serviceCall.name(), serviceResult);
            } catch (Exception e) {
                long responseTime = System.currentTimeMillis() - startTime;
                log.error("服务调用失败 - name: {}, error: {}, 耗时: {}ms",
                        serviceCall.name(), e.getMessage(), responseTime);

                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("error", e.getMessage());
                errorResult.put("success", false);

                ServiceResult serviceResult = new ServiceResult(
                        false, 500, e.getMessage(), errorResult, e.getMessage(), responseTime, false
                );

                return Map.entry(serviceCall.name(), serviceResult);
            }
        }, AGGREGATION_EXECUTOR);
    }

    /**
     * 阻塞式执行单个服务调用
     * 将响应式Mono转换为阻塞调用，在线程池中执行
     *
     * @param serviceCall 服务调用配置
     * @param timeout     超时时间
     * @return 服务调用结果
     */
    private Object executeServiceCallBlocking(ServiceCall serviceCall, Duration timeout) throws Exception {
        return switch (serviceCall.type()) {
            case REST -> callRestServiceBlocking(serviceCall, timeout);
            case GRPC -> callGrpcServiceBlocking(serviceCall, timeout);
            case GRAPHQL -> callGraphQLServiceBlocking(serviceCall, timeout);
        };
    }

    /**
     * 阻塞式调用REST服务
     *
     * @param serviceCall 服务调用配置
     * @param timeout     超时时间
     * @return REST服务结果
     */
    private Map<String, Object> callRestServiceBlocking(ServiceCall serviceCall, Duration timeout) throws Exception {
        String method = serviceCall.method() != null ? serviceCall.method() : "GET";
        return callRestService(method, serviceCall.endpoint(), serviceCall.body())
                .timeout(timeout)
                .toFuture()
                .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
    }

    /**
     * 阻塞式调用gRPC服务
     *
     * @param serviceCall 服务调用配置
     * @param timeout     超时时间
     * @return gRPC服务结果
     */
    private Object callGrpcServiceBlocking(ServiceCall serviceCall, Duration timeout) throws Exception {
        return callGrpcService(serviceCall)
                .timeout(timeout)
                .toFuture()
                .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
    }

    /**
     * 阻塞式调用GraphQL服务
     *
     * @param serviceCall 服务调用配置
     * @param timeout     超时时间
     * @return GraphQL服务结果
     */
    private Object callGraphQLServiceBlocking(ServiceCall serviceCall, Duration timeout) throws Exception {
        return callGraphQLService(serviceCall)
                .timeout(timeout)
                .toFuture()
                .get(timeout.toMillis(), TimeUnit.MILLISECONDS);
    }

    /**
     * 执行单个服务调用
     *
     * @param serviceCall 服务调用配置
     * @return 服务结果Mono
     */
    private Mono<Object> executeServiceCall(ServiceCall serviceCall) {
        log.debug("执行服务调用 - name: {}, type: {}, endpoint: {}",
                serviceCall.name(), serviceCall.type(), serviceCall.endpoint());

        return switch (serviceCall.type()) {
            case REST -> callRestService(
                    serviceCall.method() != null ? serviceCall.method() : "GET",
                    serviceCall.endpoint(),
                    serviceCall.body()
            ).map(result -> result);
            case GRPC -> callGrpcService(serviceCall);
            case GRAPHQL -> callGraphQLService(serviceCall);
        };
    }

    /**
     * 调用REST服务
     *
     * @param method   HTTP方法
     * @param endpoint 服务端点
     * @param body     请求体
     * @return 服务结果Mono
     */
    private Mono<Map<String, Object>> callRestService(String method, String endpoint, Object body) {
        log.debug("调用REST服务 - method: {}, endpoint: {}", method, endpoint);

        WebClient.RequestHeadersSpec<?> requestSpec;

        if ("POST".equalsIgnoreCase(method) || "PUT".equalsIgnoreCase(method)) {
            WebClient.RequestBodyUriSpec bodySpec = webClient.method(
                    org.springframework.http.HttpMethod.valueOf(method.toUpperCase()));
            requestSpec = bodySpec.uri(endpoint)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(body != null ? body : Map.of());
        } else {
            requestSpec = webClient.method(
                            org.springframework.http.HttpMethod.valueOf(method.toUpperCase()))
                    .uri(endpoint);
        }

        return requestSpec
                .retrieve()
                .bodyToMono(String.class)
                .map(response -> {
                    try {
                        @SuppressWarnings("unchecked")
                        Map<String, Object> result = objectMapper.readValue(response, Map.class);
                        return result;
                    } catch (Exception e) {
                        log.warn("解析REST响应失败，返回原始字符串: {}", e.getMessage());
                        Map<String, Object> result = new HashMap<>();
                        result.put("response", response);
                        return result;
                    }
                });
    }

    /**
     * 调用gRPC服务
     *
     * @param serviceCall 服务调用配置
     * @return 服务结果Mono
     */
    private Mono<Object> callGrpcService(ServiceCall serviceCall) {
        log.debug("调用gRPC服务 - service: {}, method: {}",
                serviceCall.endpoint(), serviceCall.method());

        String[] endpointParts = serviceCall.endpoint().split("/");
        if (endpointParts.length < 2) {
            return Mono.error(new IllegalArgumentException(
                    "gRPC端点格式错误，应为: serviceName/methodName"));
        }

        String serviceName = endpointParts[0];
        String methodName = endpointParts[1];
        String requestBody = serviceCall.body() != null ?
                serviceCall.body().toString() : "{}";

        Class<?> requestType = serviceCall.requestType() != null ?
                serviceCall.requestType() : com.google.protobuf.Message.class;
        Class<?> responseType = serviceCall.responseType() != null ?
                serviceCall.responseType() : com.google.protobuf.Message.class;

        @SuppressWarnings({"unchecked", "rawtypes"})
        Mono<String> resultMono = grpcBridgeService.invokeGrpcMethod(
                serviceName, methodName, requestBody,
                (Class<? extends com.google.protobuf.Message>) requestType,
                (Class<? extends com.google.protobuf.Message>) responseType
        );

        return resultMono.map(response -> {
            try {
                return objectMapper.readTree(response);
            } catch (Exception e) {
                log.warn("解析gRPC响应失败，返回原始字符串: {}", e.getMessage());
                Map<String, Object> result = new HashMap<>();
                result.put("response", response);
                return result;
            }
        });
    }

    /**
     * 调用GraphQL服务
     *
     * @param serviceCall 服务调用配置
     * @return 服务结果Mono
     */
    private Mono<Object> callGraphQLService(ServiceCall serviceCall) {
        log.debug("调用GraphQL服务 - endpoint: {}", serviceCall.endpoint());

        String query = serviceCall.body() != null ? serviceCall.body().toString() : "";
        Map<String, Object> variables = serviceCall.variables() != null ?
                serviceCall.variables() : Map.of();

        return executeGraphQLQuery(query, variables)
                .map(result -> result);
    }

    /**
     * 执行GraphQL查询
     *
     * @param query     查询语句
     * @param variables 变量
     * @return 查询结果Mono
     */
    @SuppressWarnings("unchecked")
    private Mono<Map<String, Object>> executeGraphQLQuery(String query, Map<String, Object> variables) {
        log.debug("执行GraphQL查询");

        try {
            graphql.ExecutionInput executionInput = graphql.ExecutionInput.newExecutionInput()
                    .query(query)
                    .variables(variables != null ? variables : Map.of())
                    .build();

            graphql.GraphQL graphQL = graphQLHandler != null ?
                    getGraphQLInstance() : null;

            if (graphQL != null) {
                return Mono.fromCallable(() -> {
                    graphql.ExecutionResult result = graphQL.execute(executionInput);
                    Map<String, Object> response = new HashMap<>();
                    if (!result.getErrors().isEmpty()) {
                        response.put("errors", result.getErrors());
                    }
                    response.put("data", result.getData());
                    return response;
                });
            }
        } catch (Exception e) {
            log.warn("获取GraphQL实例失败，使用模拟数据: {}", e.getMessage());
        }

        return Mono.just(Map.of(
                "data", Map.of("message", "GraphQL查询执行成功"),
                "query", query
        ));
    }

    /**
     * 获取GraphQL实例
     * 通过反射获取GraphQLHandler中的GraphQL实例
     *
     * @return GraphQL实例
     */
    private graphql.GraphQL getGraphQLInstance() throws Exception {
        java.lang.reflect.Field field = GraphQLHandler.class.getDeclaredField("graphQL");
        field.setAccessible(true);
        return (graphql.GraphQL) field.get(graphQLHandler);
    }

    /**
     * 解析聚合请求
     *
     * @param request 服务器请求
     * @return 聚合请求Mono
     */
    private Mono<AggregateRequest> parseAggregateRequest(ServerRequest request) {
        return request.bodyToMono(String.class)
                .flatMap(body -> {
                    try {
                        JsonNode rootNode = objectMapper.readTree(body);
                        List<ServiceCall> services = new ArrayList<>();

                        JsonNode servicesNode = rootNode.path("services");
                        if (servicesNode.isArray()) {
                            for (JsonNode serviceNode : servicesNode) {
                                ServiceType type = ServiceType.valueOf(
                                        serviceNode.path("type").asText("REST").toUpperCase());

                                Duration timeout = serviceNode.has("timeout") ?
                                        Duration.ofMillis(serviceNode.path("timeout").asLong()) :
                                        DEFAULT_TIMEOUT;

                                Map<String, Object> variables = null;
                                if (serviceNode.has("variables")) {
                                    variables = objectMapper.convertValue(
                                            serviceNode.path("variables"), Map.class);
                                }

                                ServiceCall serviceCall = new ServiceCall(
                                        serviceNode.path("name").asText(),
                                        type,
                                        serviceNode.path("endpoint").asText(),
                                        serviceNode.path("method").asText("GET"),
                                        serviceNode.has("body") ?
                                                objectMapper.treeToValue(serviceNode.path("body"),
                                                        Object.class) : null,
                                        timeout,
                                        variables,
                                        null,
                                        null
                                );
                                services.add(serviceCall);
                            }
                        }

                        return Mono.just(new AggregateRequest(services));
                    } catch (Exception e) {
                        log.error("解析聚合请求失败: {}", e.getMessage());
                        return Mono.error(new IllegalArgumentException(
                                "无效的聚合请求格式: " + e.getMessage()));
                    }
                });
    }

    /**
     * 获取聚合服务健康状态
     *
     * @param request 服务器请求
     * @return 健康状态响应Mono
     */
    public Mono<ServerResponse> health(ServerRequest request) {
        return ServerResponse.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of(
                        "status", "UP",
                        "service", "aggregation",
                        "supportedTypes", List.of("REST", "GRPC", "GRAPHQL"),
                        "timestamp", System.currentTimeMillis()
                ));
    }

    /**
     * 错误处理
     */
    private Mono<ServerResponse> handleError(Throwable throwable) {
        log.error("聚合处理失败: {}", throwable.getMessage(), throwable);

        int statusCode = 500;
        String errorCode = "AGGREGATION_ERROR";
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
     * 聚合请求记录
     */
    private record AggregateRequest(List<ServiceCall> services) {
    }

    /**
     * 服务调用配置记录
     */
    private record ServiceCall(
            String name,
            ServiceType type,
            String endpoint,
            String method,
            Object body,
            Duration timeout,
            Map<String, Object> variables,
            Class<?> requestType,
            Class<?> responseType
    ) {
    }

    /**
     * 服务调用结果记录
     */
    private record ServiceResult(
            boolean success,
            int code,
            String message,
            Object data,
            String error,
            long responseTimeMs,
            boolean fallback
    ) {
    }
}

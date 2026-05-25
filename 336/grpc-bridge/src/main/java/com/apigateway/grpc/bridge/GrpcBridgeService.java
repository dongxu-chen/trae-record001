package com.apigateway.grpc.bridge;

import com.apigateway.grpc.bridge.exception.GrpcBridgeException;
import com.google.protobuf.Message;
import io.grpc.CallOptions;
import io.grpc.ManagedChannel;
import io.grpc.Metadata;
import io.grpc.stub.StreamObserver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * gRPC桥接服务核心类
 * 提供动态gRPC服务调用能力，支持响应式编程风格
 * 接收JSON请求参数，返回JSON响应
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GrpcBridgeService {

    /**
     * gRPC通道工厂
     */
    private final GrpcChannelFactory channelFactory;

    /**
     * Protobuf JSON转换器
     */
    private final ProtobufJsonConverter jsonConverter;

    /**
     * gRPC客户端配置
     */
    private final GrpcClientProperties properties;

    /**
     * 方法描述符缓存
     */
    private final Map<String, GrpcMethodDescriptor> methodDescriptorCache = new ConcurrentHashMap<>();

    /**
     * gRPC元数据Header前缀
     */
    private static final String GRPC_HEADER_PREFIX = "X-Grpc-";

    /**
     * 超时Header名称
     */
    private static final String TIMEOUT_HEADER = "X-Grpc-Timeout";

    /**
     * gRPC响应元数据映射
     */
    public static final String RESPONSE_METADATA_KEY = "grpc-response-metadata";

    /**
     * 调用gRPC方法（一元调用）- 完整版本
     * 支持元数据映射和Header超时传递
     *
     * @param serviceName   服务名
     * @param methodName    方法名
     * @param jsonRequest   JSON请求参数
     * @param requestType   请求消息类型
     * @param responseType  响应消息类型
     * @param headers       HTTP请求头，用于映射到gRPC元数据
     * @param customTimeout 自定义超时时间，优先使用Header中的X-Grpc-Timeout
     * @return Mono<GrpcResponse> 包含响应JSON和元数据
     */
    public Mono<GrpcResponse> invokeGrpcMethodWithMetadata(String serviceName, String methodName,
                                                           String jsonRequest,
                                                           Class<? extends Message> requestType,
                                                           Class<? extends Message> responseType,
                                                           Map<String, String> headers,
                                                           Duration customTimeout) {
        log.debug("Invoking gRPC method with metadata: {}.{}", serviceName, methodName);

        Duration timeout = resolveTimeout(serviceName, headers, customTimeout);
        Metadata grpcMetadata = convertHeadersToMetadata(headers);

        return Mono.<GrpcResponse>create(sink -> {
            try {
                GrpcMethodDescriptor methodDescriptor = getOrCreateMethodDescriptor(
                        serviceName, methodName, requestType, responseType);

                ManagedChannel channel = channelFactory.borrowChannel(serviceName);
                try {
                    Message.Builder requestBuilder = methodDescriptor.createRequestBuilder();
                    jsonConverter.fromJson(jsonRequest, requestBuilder);
                    Message request = requestBuilder.build();

                    CallOptions callOptions = CallOptions.DEFAULT
                            .withDeadlineAfter(timeout.toMillis(), TimeUnit.MILLISECONDS);

                    io.grpc.MethodDescriptor<Message, Message> grpcMethodDescriptor =
                            methodDescriptor.toGrpcMethodDescriptor();

                    io.grpc.ClientCall<Message, Message> call =
                            channel.newCall(grpcMethodDescriptor, callOptions);

                    Metadata responseMetadata = new Metadata();

                    call.start(new StreamObserver<Message>() {
                        @Override
                        public void onNext(Message response) {
                            try {
                                String jsonResponse = jsonConverter.toJson(response);
                                Map<String, String> responseHeaders = convertMetadataToHeaders(responseMetadata);
                                GrpcResponse grpcResponse = new GrpcResponse(jsonResponse, responseHeaders);
                                sink.success(grpcResponse);
                            } catch (Exception e) {
                                sink.error(new GrpcBridgeException("RESPONSE_PARSE_ERROR",
                                        "Failed to parse gRPC response: " + e.getMessage(), e));
                            }
                        }

                        @Override
                        public void onError(Throwable t) {
                            log.error("gRPC call failed for {}.{}: {}", serviceName, methodName, t.getMessage());
                            sink.error(new GrpcBridgeException("GRPC_CALL_ERROR",
                                    "gRPC call failed: " + t.getMessage(), t));
                        }

                        @Override
                        public void onCompleted() {
                            log.debug("gRPC call completed for {}.{}", serviceName, methodName);
                        }
                    }, grpcMetadata);

                    call.sendMessage(request);
                    call.halfClose();
                    call.request(1);

                } finally {
                    channelFactory.returnChannel(serviceName);
                }
            } catch (Exception e) {
                log.error("Error invoking gRPC method {}.{}: {}", serviceName, methodName, e.getMessage());
                sink.error(e);
            }
        }).onErrorMap(this::mapError);
    }

    /**
     * 调用gRPC方法（一元调用）- 简化版本
     *
     * @param serviceName   服务名
     * @param methodName    方法名
     * @param jsonRequest   JSON请求参数
     * @param requestType   请求消息类型
     * @param responseType  响应消息类型
     * @return Mono<String> JSON响应
     */
    public Mono<String> invokeGrpcMethod(String serviceName, String methodName, String jsonRequest,
                                         Class<? extends Message> requestType,
                                         Class<? extends Message> responseType) {
        return invokeGrpcMethodWithMetadata(serviceName, methodName, jsonRequest,
                requestType, responseType, Map.of(), null)
                .map(GrpcResponse::response);
    }

    /**
     * 解析超时时间
     * 优先级: Header X-Grpc-Timeout > 自定义Timeout > 服务配置
     *
     * @param serviceName   服务名
     * @param headers       请求头
     * @param customTimeout 自定义超时
     * @return 最终超时时间
     */
    private Duration resolveTimeout(String serviceName, Map<String, String> headers, Duration customTimeout) {
        if (headers != null && headers.containsKey(TIMEOUT_HEADER)) {
            try {
                String timeoutStr = headers.get(TIMEOUT_HEADER);
                long timeoutMs = Long.parseLong(timeoutStr);
                log.debug("使用Header传递的超时时间: {}ms", timeoutMs);
                return Duration.ofMillis(timeoutMs);
            } catch (NumberFormatException e) {
                log.warn("解析Header超时时间失败，使用默认配置: {}", e.getMessage());
            }
        }

        if (customTimeout != null) {
            log.debug("使用自定义超时时间: {}ms", customTimeout.toMillis());
            return customTimeout;
        }

        return properties.getDeadline(serviceName);
    }

    /**
     * 将HTTP Header转换为gRPC Metadata
     * 支持X-Grpc-*前缀的Header自动映射
     *
     * @param headers HTTP请求头
     * @return gRPC Metadata
     */
    private Metadata convertHeadersToMetadata(Map<String, String> headers) {
        Metadata metadata = new Metadata();
        if (headers == null || headers.isEmpty()) {
            return metadata;
        }

        headers.forEach((key, value) -> {
            if (key.startsWith(GRPC_HEADER_PREFIX) && !key.equals(TIMEOUT_HEADER)) {
                String metadataKey = key.substring(GRPC_HEADER_PREFIX.length()).toLowerCase();
                Metadata.Key<String> grpcKey = Metadata.Key.of(metadataKey, Metadata.ASCII_STRING_MARSHALLER);
                metadata.put(grpcKey, value);
                log.debug("映射HTTP Header到gRPC元数据: {} -> {}: {}", key, metadataKey, value);
            }
        });

        return metadata;
    }

    /**
     * 将gRPC Metadata转换为HTTP响应头
     *
     * @param metadata gRPC元数据
     * @return HTTP响应头Map
     */
    private Map<String, String> convertMetadataToHeaders(Metadata metadata) {
        Map<String, String> headers = new HashMap<>();
        if (metadata == null) {
            return headers;
        }

        for (String key : metadata.keys()) {
            if (!key.endsWith(Metadata.BINARY_HEADER_SUFFIX)) {
                Metadata.Key<String> strKey = Metadata.Key.of(key, Metadata.ASCII_STRING_MARSHALLER);
                String value = metadata.get(strKey);
                if (value != null) {
                    String headerKey = GRPC_HEADER_PREFIX + key;
                    headers.put(headerKey, value);
                    log.debug("映射gRPC元数据到HTTP Header: {} -> {}: {}", key, headerKey, value);
                }
            }
        }

        return headers;
    }

    /**
     * gRPC响应记录，包含响应体和元数据
     */
    public record GrpcResponse(String response, Map<String, String> headers) {
    }

    /**
     * 调用gRPC方法，使用Map作为请求参数
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requestMap   请求参数Map
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return Mono<String> JSON响应
     */
    public Mono<String> invokeGrpcMethod(String serviceName, String methodName,
                                         Map<String, Object> requestMap,
                                         Class<? extends Message> requestType,
                                         Class<? extends Message> responseType) {
        String jsonRequest = jsonConverter.toJson(jsonConverter.toJsonNode(
                jsonConverter.wrapResponse(true, requestMap, null)));
        return invokeGrpcMethod(serviceName, methodName, jsonRequest, requestType, responseType);
    }

    /**
     * 调用gRPC方法，使用Map作为请求参数（简化版本）
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requestMap   请求参数Map
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return Mono<String> JSON响应
     */
    public Mono<String> invokeGrpcMethodWithMap(String serviceName, String methodName,
                                                Map<String, Object> requestMap,
                                                Class<? extends Message> requestType,
                                                Class<? extends Message> responseType) {
        try {
            String jsonRequest = jsonConverter.toJson(jsonConverter.toJsonNode(requestMap));
            return invokeGrpcMethod(serviceName, methodName, jsonRequest, requestType, responseType);
        } catch (Exception e) {
            return Mono.error(e);
        }
    }

    /**
     * 调用服务端流式gRPC方法
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param jsonRequest  JSON请求参数
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return Flux<String> JSON响应流
     */
    public Flux<String> invokeServerStreaming(String serviceName, String methodName, String jsonRequest,
                                              Class<? extends Message> requestType,
                                              Class<? extends Message> responseType) {
        log.debug("Invoking server streaming gRPC method: {}.{}", serviceName, methodName);

        return Flux.<String>create(sink -> {
            try {
                GrpcMethodDescriptor methodDescriptor = GrpcMethodDescriptor.createReactive(
                        serviceName, methodName, requestType, responseType,
                        io.grpc.MethodDescriptor.MethodType.SERVER_STREAMING);

                ManagedChannel channel = channelFactory.borrowChannel(serviceName);
                try {
                    Message.Builder requestBuilder = methodDescriptor.createRequestBuilder();
                    jsonConverter.fromJson(jsonRequest, requestBuilder);
                    Message request = requestBuilder.build();

                    DeadlineOption deadlineOption = getDeadlineOption(serviceName);

                    CallOptions callOptions = CallOptions.DEFAULT
                            .withDeadlineAfter(deadlineOption.timeout(), deadlineOption.unit());

                    io.grpc.MethodDescriptor<Message, Message> grpcMethodDescriptor =
                            methodDescriptor.toGrpcMethodDescriptor();

                    io.grpc.ClientCall<Message, Message> call =
                            channel.newCall(grpcMethodDescriptor, callOptions);

                    call.start(new StreamObserver<Message>() {
                        @Override
                        public void onNext(Message response) {
                            try {
                                String jsonResponse = jsonConverter.toJson(response);
                                sink.next(jsonResponse);
                            } catch (Exception e) {
                                sink.error(new GrpcBridgeException("RESPONSE_PARSE_ERROR",
                                        "Failed to parse gRPC response: " + e.getMessage(), e));
                            }
                        }

                        @Override
                        public void onError(Throwable t) {
                            log.error("gRPC streaming call failed for {}.{}: {}",
                                    serviceName, methodName, t.getMessage());
                            sink.error(new GrpcBridgeException("GRPC_CALL_ERROR",
                                    "gRPC call failed: " + t.getMessage(), t));
                        }

                        @Override
                        public void onCompleted() {
                            log.debug("gRPC streaming call completed for {}.{}", serviceName, methodName);
                            sink.complete();
                        }
                    }, io.grpc.Metadata());

                    call.sendMessage(request);
                    call.halfClose();
                    call.request(Integer.MAX_VALUE);

                } finally {
                    channelFactory.returnChannel(serviceName);
                }
            } catch (Exception e) {
                log.error("Error invoking gRPC streaming method {}.{}: {}",
                        serviceName, methodName, e.getMessage());
                sink.error(e);
            }
        }).onErrorMap(this::mapError);
    }

    /**
     * 调用客户端流式gRPC方法
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requests     请求流
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return Mono<String> JSON响应
     */
    public Mono<String> invokeClientStreaming(String serviceName, String methodName,
                                              Flux<String> requests,
                                              Class<? extends Message> requestType,
                                              Class<? extends Message> responseType) {
        log.debug("Invoking client streaming gRPC method: {}.{}", serviceName, methodName);

        Sinks.One<String> responseSink = Sinks.one();

        return Mono.defer(() -> {
            try {
                GrpcMethodDescriptor methodDescriptor = GrpcMethodDescriptor.createReactive(
                        serviceName, methodName, requestType, responseType,
                        io.grpc.MethodDescriptor.MethodType.CLIENT_STREAMING);

                ManagedChannel channel = channelFactory.borrowChannel(serviceName);

                DeadlineOption deadlineOption = getDeadlineOption(serviceName);

                CallOptions callOptions = CallOptions.DEFAULT
                        .withDeadlineAfter(deadlineOption.timeout(), deadlineOption.unit());

                io.grpc.MethodDescriptor<Message, Message> grpcMethodDescriptor =
                        methodDescriptor.toGrpcMethodDescriptor();

                io.grpc.ClientCall<Message, Message> call =
                        channel.newCall(grpcMethodDescriptor, callOptions);

                call.start(new StreamObserver<Message>() {
                    @Override
                    public void onNext(Message response) {
                        try {
                            String jsonResponse = jsonConverter.toJson(response);
                            responseSink.tryEmitValue(jsonResponse);
                        } catch (Exception e) {
                            responseSink.tryEmitError(new GrpcBridgeException("RESPONSE_PARSE_ERROR",
                                    "Failed to parse gRPC response: " + e.getMessage(), e));
                        }
                    }

                    @Override
                    public void onError(Throwable t) {
                        log.error("gRPC client streaming call failed for {}.{}: {}",
                                serviceName, methodName, t.getMessage());
                        responseSink.tryEmitError(new GrpcBridgeException("GRPC_CALL_ERROR",
                                "gRPC call failed: " + t.getMessage(), t));
                    }

                    @Override
                    public void onCompleted() {
                        log.debug("gRPC client streaming call completed for {}.{}",
                                serviceName, methodName);
                    }
                }, io.grpc.Metadata());

                requests.subscribe(
                        jsonRequest -> {
                            try {
                                Message.Builder requestBuilder = methodDescriptor.createRequestBuilder();
                                jsonConverter.fromJson(jsonRequest, requestBuilder);
                                call.sendMessage(requestBuilder.build());
                            } catch (Exception e) {
                                log.error("Failed to send request: {}", e.getMessage());
                                call.cancel("Request parsing failed", e);
                                responseSink.tryEmitError(e);
                            }
                        },
                        error -> {
                            log.error("Request stream error: {}", error.getMessage());
                            call.cancel("Request stream error", error);
                            responseSink.tryEmitError(error);
                        },
                        () -> {
                            call.halfClose();
                            call.request(1);
                        }
                );

                call.request(1);

                return responseSink.asMono()
                        .doFinally(signalType -> channelFactory.returnChannel(serviceName));

            } catch (Exception e) {
                log.error("Error invoking gRPC client streaming method {}.{}: {}",
                        serviceName, methodName, e.getMessage());
                return Mono.error(e);
            }
        }).onErrorMap(this::mapError);
    }

    /**
     * 调用双向流式gRPC方法
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requests     请求流
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return Flux<String> JSON响应流
     */
    public Flux<String> invokeBidirectionalStreaming(String serviceName, String methodName,
                                                     Flux<String> requests,
                                                     Class<? extends Message> requestType,
                                                     Class<? extends Message> responseType) {
        log.debug("Invoking bidirectional streaming gRPC method: {}.{}", serviceName, methodName);

        return Flux.<String>create(sink -> {
            try {
                GrpcMethodDescriptor methodDescriptor = GrpcMethodDescriptor.createReactive(
                        serviceName, methodName, requestType, responseType,
                        io.grpc.MethodDescriptor.MethodType.BIDI_STREAMING);

                ManagedChannel channel = channelFactory.borrowChannel(serviceName);

                DeadlineOption deadlineOption = getDeadlineOption(serviceName);

                CallOptions callOptions = CallOptions.DEFAULT
                        .withDeadlineAfter(deadlineOption.timeout(), deadlineOption.unit());

                io.grpc.MethodDescriptor<Message, Message> grpcMethodDescriptor =
                        methodDescriptor.toGrpcMethodDescriptor();

                io.grpc.ClientCall<Message, Message> call =
                        channel.newCall(grpcMethodDescriptor, callOptions);

                call.start(new StreamObserver<Message>() {
                    @Override
                    public void onNext(Message response) {
                        try {
                            String jsonResponse = jsonConverter.toJson(response);
                            sink.next(jsonResponse);
                        } catch (Exception e) {
                            sink.error(new GrpcBridgeException("RESPONSE_PARSE_ERROR",
                                    "Failed to parse gRPC response: " + e.getMessage(), e));
                        }
                    }

                    @Override
                    public void onError(Throwable t) {
                        log.error("gRPC bidirectional streaming call failed for {}.{}: {}",
                                serviceName, methodName, t.getMessage());
                        sink.error(new GrpcBridgeException("GRPC_CALL_ERROR",
                                "gRPC call failed: " + t.getMessage(), t));
                    }

                    @Override
                    public void onCompleted() {
                        log.debug("gRPC bidirectional streaming call completed for {}.{}",
                                serviceName, methodName);
                        sink.complete();
                    }
                }, io.grpc.Metadata());

                requests.subscribe(
                        jsonRequest -> {
                            try {
                                Message.Builder requestBuilder = methodDescriptor.createRequestBuilder();
                                jsonConverter.fromJson(jsonRequest, requestBuilder);
                                call.sendMessage(requestBuilder.build());
                            } catch (Exception e) {
                                log.error("Failed to send request: {}", e.getMessage());
                                call.cancel("Request parsing failed", e);
                                sink.error(e);
                            }
                        },
                        error -> {
                            log.error("Request stream error: {}", error.getMessage());
                            call.cancel("Request stream error", error);
                            sink.error(error);
                        },
                        () -> {
                            call.halfClose();
                        }
                );

                call.request(Integer.MAX_VALUE);

                sink.onDispose(() -> {
                    if (!call.isCancelled()) {
                        call.cancel("Client disposed", null);
                    }
                    channelFactory.returnChannel(serviceName);
                });

            } catch (Exception e) {
                log.error("Error invoking gRPC bidirectional streaming method {}.{}: {}",
                        serviceName, methodName, e.getMessage());
                sink.error(e);
            }
        }).onErrorMap(this::mapError);
    }

    /**
     * 获取或创建方法描述符
     */
    private GrpcMethodDescriptor getOrCreateMethodDescriptor(String serviceName, String methodName,
                                                             Class<? extends Message> requestType,
                                                             Class<? extends Message> responseType) {
        String cacheKey = serviceName + "/" + methodName;
        return methodDescriptorCache.computeIfAbsent(cacheKey, key ->
                GrpcMethodDescriptor.create(serviceName, methodName, requestType, responseType));
    }

    /**
     * 获取截止时间配置
     */
    private DeadlineOption getDeadlineOption(String serviceName) {
        Duration deadline = properties.getDeadline(serviceName);
        return new DeadlineOption(deadline.toMillis(), TimeUnit.MILLISECONDS);
    }

    /**
     * 映射异常为GrpcBridgeException
     */
    private Throwable mapError(Throwable throwable) {
        if (throwable instanceof GrpcBridgeException) {
            return throwable;
        }
        return new GrpcBridgeException("GRPC_BRIDGE_ERROR",
                "gRPC bridge error: " + throwable.getMessage(), throwable);
    }

    /**
     * 截止时间选项记录
     */
    private record DeadlineOption(long timeout, TimeUnit unit) {
    }

    /**
     * 检查服务连接是否健康
     *
     * @param serviceName 服务名
     * @return Mono<Boolean> 健康状态
     */
    public Mono<Boolean> checkServiceHealth(String serviceName) {
        return Mono.fromCallable(() -> channelFactory.isChannelHealthy(serviceName));
    }

    /**
     * 获取当前活跃连接数
     *
     * @return Mono<Integer> 活跃连接数
     */
    public Mono<Integer> getActiveConnectionCount() {
        return Mono.fromCallable(channelFactory::getActiveChannelCount);
    }

    /**
     * 关闭指定服务的连接
     *
     * @param serviceName 服务名
     * @return Mono<Void>
     */
    public Mono<Void> closeServiceConnection(String serviceName) {
        return Mono.fromRunnable(() -> {
            channelFactory.closeChannel(serviceName);
            methodDescriptorCache.entrySet().removeIf(entry ->
                    entry.getKey().startsWith(serviceName + "/"));
        });
    }
}

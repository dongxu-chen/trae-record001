package com.apigateway.grpc.bridge;

import com.apigateway.grpc.bridge.exception.GrpcBridgeException;
import com.google.protobuf.Descriptors;
import com.google.protobuf.DynamicMessage;
import com.google.protobuf.Message;
import io.grpc.MethodDescriptor;
import io.grpc.protobuf.ProtoUtils;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.lang.reflect.Method;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * gRPC方法描述符类
 * 用于动态描述gRPC服务方法，支持服务反射和动态调用
 * 包含请求/响应类型、服务名、方法名等元数据
 */
@Slf4j
@Data
@Builder
public class GrpcMethodDescriptor {

    /**
     * 服务名（完整包名+服务名）
     */
    private String serviceName;

    /**
     * 方法名
     */
    private String methodName;

    /**
     * 完整方法名（/服务名/方法名）
     */
    private String fullMethodName;

    /**
     * 请求消息类型
     */
    private Class<? extends Message> requestType;

    /**
     * 响应消息类型
     */
    private Class<? extends Message> responseType;

    /**
     * 请求消息描述符
     */
    private Descriptors.Descriptor requestDescriptor;

    /**
     * 响应消息描述符
     */
    private Descriptors.Descriptor responseDescriptor;

    /**
     * 方法类型（一元、客户端流、服务端流、双向流）
     */
    private MethodDescriptor.MethodType methodType;

    /**
     * 是否为响应式调用
     */
    private boolean reactive;

    /**
     * 方法描述符缓存
     */
    private static final Map<String, GrpcMethodDescriptor> DESCRIPTOR_CACHE = new ConcurrentHashMap<>();

    /**
     * gRPC方法描述符缓存
     */
    private static final Map<String, MethodDescriptor<Message, Message>> METHOD_DESCRIPTOR_CACHE =
            new ConcurrentHashMap<>();

    /**
     * 创建gRPC方法描述符
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @return GrpcMethodDescriptor实例
     */
    public static GrpcMethodDescriptor create(String serviceName, String methodName,
                                              Class<? extends Message> requestType,
                                              Class<? extends Message> responseType) {
        String cacheKey = serviceName + "/" + methodName;

        return DESCRIPTOR_CACHE.computeIfAbsent(cacheKey, key -> {
            try {
                String fullMethodName = "/" + serviceName + "/" + methodName;

                Descriptors.Descriptor requestDescriptor = getMessageDescriptor(requestType);
                Descriptors.Descriptor responseDescriptor = getMessageDescriptor(responseType);

                return GrpcMethodDescriptor.builder()
                        .serviceName(serviceName)
                        .methodName(methodName)
                        .fullMethodName(fullMethodName)
                        .requestType(requestType)
                        .responseType(responseType)
                        .requestDescriptor(requestDescriptor)
                        .responseDescriptor(responseDescriptor)
                        .methodType(MethodDescriptor.MethodType.UNARY)
                        .reactive(false)
                        .build();
            } catch (Exception e) {
                throw new GrpcBridgeException("DESCRIPTOR_CREATE_ERROR",
                        String.format("Failed to create method descriptor for %s.%s: %s",
                                serviceName, methodName, e.getMessage()), e);
            }
        });
    }

    /**
     * 创建响应式gRPC方法描述符
     *
     * @param serviceName  服务名
     * @param methodName   方法名
     * @param requestType  请求消息类型
     * @param responseType 响应消息类型
     * @param methodType   方法类型
     * @return GrpcMethodDescriptor实例
     */
    public static GrpcMethodDescriptor createReactive(String serviceName, String methodName,
                                                      Class<? extends Message> requestType,
                                                      Class<? extends Message> responseType,
                                                      MethodDescriptor.MethodType methodType) {
        GrpcMethodDescriptor descriptor = create(serviceName, methodName, requestType, responseType);
        descriptor.setMethodType(methodType);
        descriptor.setReactive(true);
        return descriptor;
    }

    /**
     * 获取消息类型的描述符
     *
     * @param messageType 消息类型
     * @return 消息描述符
     */
    public static Descriptors.Descriptor getMessageDescriptor(Class<? extends Message> messageType) {
        try {
            Method getDescriptorMethod = messageType.getMethod("getDescriptor");
            return (Descriptors.Descriptor) getDescriptorMethod.invoke(null);
        } catch (Exception e) {
            throw new GrpcBridgeException("DESCRIPTOR_RESOLVE_ERROR",
                    "Failed to resolve descriptor for message type: " + messageType.getName(), e);
        }
    }

    /**
     * 创建请求消息Builder
     *
     * @return 消息Builder实例
     */
    public Message.Builder createRequestBuilder() {
        try {
            Method newBuilderMethod = requestType.getMethod("newBuilder");
            return (Message.Builder) newBuilderMethod.invoke(null);
        } catch (Exception e) {
            throw new GrpcBridgeException("BUILDER_CREATE_ERROR",
                    "Failed to create request builder for: " + requestType.getName(), e);
        }
    }

    /**
     * 创建响应消息Builder
     *
     * @return 消息Builder实例
     */
    public Message.Builder createResponseBuilder() {
        try {
            Method newBuilderMethod = responseType.getMethod("newBuilder");
            return (Message.Builder) newBuilderMethod.invoke(null);
        } catch (Exception e) {
            throw new GrpcBridgeException("BUILDER_CREATE_ERROR",
                    "Failed to create response builder for: " + responseType.getName(), e);
        }
    }

    /**
     * 创建请求消息的默认实例
     *
     * @return 默认请求消息实例
     */
    public Message getDefaultRequestInstance() {
        try {
            Method getDefaultInstanceMethod = requestType.getMethod("getDefaultInstance");
            return (Message) getDefaultInstanceMethod.invoke(null);
        } catch (Exception e) {
            throw new GrpcBridgeException("DEFAULT_INSTANCE_ERROR",
                    "Failed to get default instance for: " + requestType.getName(), e);
        }
    }

    /**
     * 创建响应消息的默认实例
     *
     * @return 默认响应消息实例
     */
    public Message getDefaultResponseInstance() {
        try {
            Method getDefaultInstanceMethod = responseType.getMethod("getDefaultInstance");
            return (Message) getDefaultInstanceMethod.invoke(null);
        } catch (Exception e) {
            throw new GrpcBridgeException("DEFAULT_INSTANCE_ERROR",
                    "Failed to get default instance for: " + responseType.getName(), e);
        }
    }

    /**
     * 转换为gRPC MethodDescriptor
     *
     * @return gRPC MethodDescriptor
     */
    @SuppressWarnings("unchecked")
    public MethodDescriptor<Message, Message> toGrpcMethodDescriptor() {
        return METHOD_DESCRIPTOR_CACHE.computeIfAbsent(fullMethodName, key -> {
            Message defaultRequest = getDefaultRequestInstance();
            Message defaultResponse = getDefaultResponseInstance();

            return MethodDescriptor.<Message, Message>newBuilder()
                    .setType(methodType)
                    .setFullMethodName(fullMethodName)
                    .setRequestMarshaller(ProtoUtils.marshaller(defaultRequest))
                    .setResponseMarshaller(ProtoUtils.marshaller(defaultResponse))
                    .build();
        });
    }

    /**
     * 创建动态消息Builder
     *
     * @param descriptor 消息描述符
     * @return 动态消息Builder
     */
    public static DynamicMessage.Builder createDynamicBuilder(Descriptors.Descriptor descriptor) {
        return DynamicMessage.newBuilder(descriptor);
    }

    /**
     * 检查方法描述符是否已缓存
     *
     * @param serviceName 服务名
     * @param methodName  方法名
     * @return true表示已缓存
     */
    public static boolean isCached(String serviceName, String methodName) {
        String cacheKey = serviceName + "/" + methodName;
        return DESCRIPTOR_CACHE.containsKey(cacheKey);
    }

    /**
     * 清除方法描述符缓存
     */
    public static void clearCache() {
        DESCRIPTOR_CACHE.clear();
        METHOD_DESCRIPTOR_CACHE.clear();
        log.info("Cleared all method descriptor caches");
    }

    /**
     * 获取缓存的方法描述符数量
     *
     * @return 缓存数量
     */
    public static int getCacheSize() {
        return DESCRIPTOR_CACHE.size();
    }
}

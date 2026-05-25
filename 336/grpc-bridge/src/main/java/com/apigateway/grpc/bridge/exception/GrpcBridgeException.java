package com.apigateway.grpc.bridge.exception;

import lombok.Getter;

/**
 * gRPC桥接自定义异常类
 * 用于封装gRPC调用过程中发生的各种异常
 */
@Getter
public class GrpcBridgeException extends RuntimeException {

    /**
     * 错误码
     */
    private final String errorCode;

    /**
     * 构造函数
     *
     * @param message 错误消息
     */
    public GrpcBridgeException(String message) {
        super(message);
        this.errorCode = "GRPC_BRIDGE_ERROR";
    }

    /**
     * 构造函数
     *
     * @param errorCode 错误码
     * @param message   错误消息
     */
    public GrpcBridgeException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    /**
     * 构造函数
     *
     * @param message 错误消息
     * @param cause   原始异常
     */
    public GrpcBridgeException(String message, Throwable cause) {
        super(message, cause);
        this.errorCode = "GRPC_BRIDGE_ERROR";
    }

    /**
     * 构造函数
     *
     * @param errorCode 错误码
     * @param message   错误消息
     * @param cause     原始异常
     */
    public GrpcBridgeException(String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }
}

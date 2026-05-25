package com.apigateway.core.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 统一API响应类
 *
 * @param <T> 响应数据类型
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {

    /**
     * 是否成功
     */
    private Boolean success;

    /**
     * 响应状态码
     */
    private Integer code;

    /**
     * 响应消息
     */
    private String message;

    /**
     * 响应数据
     */
    private T data;

    /**
     * 响应时间戳
     */
    private LocalDateTime timestamp;

    /**
     * 成功响应（无数据）
     *
     * @param <T> 数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> success() {
        return ApiResponse.<T>builder()
                .success(true)
                .code(200)
                .message("操作成功")
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 成功响应（带数据）
     *
     * @param data 响应数据
     * @param <T>  数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> success(T data) {
        return ApiResponse.<T>builder()
                .success(true)
                .code(200)
                .message("操作成功")
                .data(data)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 成功响应（带消息和数据）
     *
     * @param message 响应消息
     * @param data    响应数据
     * @param <T>     数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> success(String message, T data) {
        return ApiResponse.<T>builder()
                .success(true)
                .code(200)
                .message(message)
                .data(data)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 错误响应
     *
     * @param code    错误码
     * @param message 错误消息
     * @param <T>     数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> error(Integer code, String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .code(code)
                .message(message)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 错误响应（默认500状态码）
     *
     * @param message 错误消息
     * @param <T>     数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> error(String message) {
        return error(500, message);
    }

    /**
     * 降级响应
     *
     * @param message 降级消息
     * @param <T>     数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> fallback(String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .code(503)
                .message(message != null ? message : "服务暂时不可用，请稍后重试")
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 降级响应（无消息）
     *
     * @param <T> 数据类型
     * @return ApiResponse实例
     */
    public static <T> ApiResponse<T> fallback() {
        return fallback(null);
    }
}

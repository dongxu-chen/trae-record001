package com.apigateway.core.dto.exception;

import com.apigateway.core.dto.ApiResponse;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.support.WebExchangeBindException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.server.ServerWebInputException;

import java.util.stream.Collectors;

/**
 * 全局异常处理器
 * 处理各种异常并返回统一的ApiResponse格式
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 处理参数校验异常（WebFlux）
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(WebExchangeBindException.class)
    public ResponseEntity<ApiResponse<Void>> handleWebExchangeBindException(WebExchangeBindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        return ResponseEntity.badRequest()
                .body(ApiResponse.error(400, "参数校验失败: " + message));
    }

    /**
     * 处理参数校验异常（MVC）
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleMethodArgumentNotValidException(
            MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        return ResponseEntity.badRequest()
                .body(ApiResponse.error(400, "参数校验失败: " + message));
    }

    /**
     * 处理参数绑定异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<ApiResponse<Void>> handleBindException(BindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        log.warn("参数绑定失败: {}", message);
        return ResponseEntity.badRequest()
                .body(ApiResponse.error(400, "参数绑定失败: " + message));
    }

    /**
     * 处理非法参数异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgumentException(IllegalArgumentException e) {
        log.warn("非法参数: {}", e.getMessage());
        return ResponseEntity.badRequest()
                .body(ApiResponse.error(400, e.getMessage()));
    }

    /**
     * 处理请求输入异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(ServerWebInputException.class)
    public ResponseEntity<ApiResponse<Void>> handleServerWebInputException(ServerWebInputException e) {
        log.warn("请求输入错误: {}", e.getMessage());
        return ResponseEntity.badRequest()
                .body(ApiResponse.error(400, "请求输入错误: " + e.getReason()));
    }

    /**
     * 处理HTTP状态异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<ApiResponse<Void>> handleResponseStatusException(ResponseStatusException e) {
        log.warn("HTTP状态异常: {} - {}", e.getStatusCode(), e.getReason());
        return ResponseEntity.status(e.getStatusCode())
                .body(ApiResponse.error(e.getStatusCode().value(), e.getReason()));
    }

    /**
     * 处理熔断器异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(CallNotPermittedException.class)
    public ResponseEntity<ApiResponse<Void>> handleCallNotPermittedException(CallNotPermittedException e) {
        log.warn("熔断器已打开: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiResponse.fallback("服务暂时不可用，请稍后重试"));
    }

    /**
     * 处理超时异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(java.util.concurrent.TimeoutException.class)
    public ResponseEntity<ApiResponse<Void>> handleTimeoutException(java.util.concurrent.TimeoutException e) {
        log.warn("服务调用超时: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT)
                .body(ApiResponse.error(504, "服务调用超时"));
    }

    /**
     * 处理空指针异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(NullPointerException.class)
    public ResponseEntity<ApiResponse<Void>> handleNullPointerException(NullPointerException e) {
        log.error("空指针异常", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(500, "系统内部错误"));
    }

    /**
     * 处理运行时异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<ApiResponse<Void>> handleRuntimeException(RuntimeException e) {
        log.error("运行时异常: {}", e.getMessage(), e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(500, "运行时错误: " + e.getMessage()));
    }

    /**
     * 处理所有其他异常
     *
     * @param e 异常对象
     * @return 统一错误响应
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleException(Exception e) {
        log.error("系统异常: {}", e.getMessage(), e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(500, "系统内部错误，请联系管理员"));
    }
}

package com.ratelimit.center.handler;

import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.alibaba.csp.sentinel.slots.block.authority.AuthorityException;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeException;
import com.alibaba.csp.sentinel.slots.block.flow.FlowException;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowException;
import com.alibaba.csp.sentinel.slots.system.SystemBlockException;
import com.ratelimit.center.common.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import javax.servlet.http.HttpServletRequest;
import java.util.stream.Collectors;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(FlowException.class)
    @ResponseStatus(HttpStatus.TOO_MANY_REQUESTS)
    public Result<Void> handleFlowException(FlowException e, HttpServletRequest request) {
        log.warn("Flow limit triggered: {}, resource: {}, rule: {}",
                request.getRequestURI(), e.getRuleLimitApp(), e.getRule());
        return Result.fail(429, "请求过于频繁，请稍后再试");
    }

    @ExceptionHandler(DegradeException.class)
    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    public Result<Void> handleDegradeException(DegradeException e, HttpServletRequest request) {
        log.warn("Degrade triggered: {}, resource: {}", request.getRequestURI(), e.getRule());
        return Result.fail(503, "服务暂不可用，请稍后再试");
    }

    @ExceptionHandler(ParamFlowException.class)
    @ResponseStatus(HttpStatus.TOO_MANY_REQUESTS)
    public Result<Void> handleParamFlowException(ParamFlowException e, HttpServletRequest request) {
        log.warn("Param flow limit triggered: {}, resource: {}", request.getRequestURI(), e.getResourceName());
        return Result.fail(429, "请求参数访问频率过高");
    }

    @ExceptionHandler(SystemBlockException.class)
    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    public Result<Void> handleSystemBlockException(SystemBlockException e, HttpServletRequest request) {
        log.warn("System block triggered: {}, resource: {}", request.getRequestURI(), e.getResourceName());
        return Result.fail(503, "系统负载过高，请稍后再试");
    }

    @ExceptionHandler(AuthorityException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public Result<Void> handleAuthorityException(AuthorityException e, HttpServletRequest request) {
        log.warn("Authority limit triggered: {}, resource: {}", request.getRequestURI(), e.getResourceName());
        return Result.fail(403, "无权限访问");
    }

    @ExceptionHandler(BlockException.class)
    @ResponseStatus(HttpStatus.TOO_MANY_REQUESTS)
    public Result<Void> handleBlockException(BlockException e, HttpServletRequest request) {
        log.warn("Blocked by Sentinel: {}, resource: {}", request.getRequestURI(), e.getRuleLimitApp());
        return Result.fail(429, "请求被限流");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        return Result.fail(400, message);
    }

    @ExceptionHandler(BindException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleBindException(BindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining(", "));
        return Result.fail(400, message);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleIllegalArgumentException(IllegalArgumentException e) {
        log.warn("Invalid argument: {}", e.getMessage());
        return Result.fail(400, e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception e, HttpServletRequest request) {
        log.error("Unhandled exception occurred: {}", request.getRequestURI(), e);
        return Result.fail(500, "系统内部错误");
    }
}

package com.pushplatform.config;

import com.pushplatform.common.core.Result;
import com.pushplatform.push.reactive.BackPressureController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import reactor.core.publisher.Mono;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BackPressureController.BackPressureException.class)
    @ResponseStatus(HttpStatus.TOO_MANY_REQUESTS)
    public Mono<Result<Void>> handleBackPressureException(BackPressureController.BackPressureException e) {
        logger.warn("Back pressure triggered: {}", e.getMessage());
        return Mono.just(Result.error(429, e.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Mono<Result<Void>> handleIllegalArgumentException(IllegalArgumentException e) {
        logger.warn("Invalid request: {}", e.getMessage());
        return Mono.just(Result.error(400, e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Mono<Result<Void>> handleException(Exception e) {
        logger.error("Internal server error", e);
        return Mono.just(Result.error(500, "Internal server error"));
    }
}

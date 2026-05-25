package com.apigateway.core;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * API网关启动类
 * 基于Spring Cloud Gateway构建的响应式API网关
 * 支持REST、GraphQL、gRPC、聚合等多种协议路由
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@SpringBootApplication
@EnableScheduling
public class ApiGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}

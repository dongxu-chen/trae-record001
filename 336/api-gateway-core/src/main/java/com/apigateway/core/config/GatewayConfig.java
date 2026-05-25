package com.apigateway.core.config;

import com.apigateway.core.handler.AggregationHandler;
import com.apigateway.core.handler.GraphQLHandler;
import com.apigateway.core.handler.GrpcBridgeHandler;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.ServerResponse;

import static org.springframework.web.reactive.function.server.RouterFunctions.route;

/**
 * 网关路由配置类
 * 使用代码方式定义路由规则，支持多种协议的请求路由
 * 包含REST、GraphQL、gRPC、聚合等四种路由规则
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Configuration
public class GatewayConfig {

    /**
     * 配置网关路由定位器
     * 定义四个主要路由规则：
     * 1. REST API路由 - /api/rest/** -> 路由到REST后端服务（http://localhost:8081）
     * 2. GraphQL路由 - /api/graphql/** -> 由函数式路由处理
     * 3. gRPC桥接路由 - /api/grpc/** -> 由函数式路由处理
     * 4. 聚合路由 - /api/aggregate/** -> 由函数式路由处理
     *
     * @param builder 路由构建器
     * @return 路由定位器
     */
    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                // REST API路由 - 转发到后端模拟服务
                .route("rest_route", r -> r
                        .path("/api/rest/**")
                        .filters(f -> f
                                .stripPrefix(2)
                                .addRequestHeader("X-Gateway-Id", "api-gateway-core")
                        )
                        .uri("http://localhost:8081"))
                .build();
    }

    /**
     * 函数式路由配置 - GraphQL处理器
     * 处理/api/graphql/**的所有请求
     *
     * @param handler GraphQL处理器
     * @return 路由函数
     */
    @Bean
    public RouterFunction<ServerResponse> graphqlRouter(GraphQLHandler handler) {
        return route()
                .GET("/api/graphql", handler::handleGraphQLGet)
                .POST("/api/graphql", handler::handleGraphQLPost)
                .GET("/api/graphql/schema", handler::getSchema)
                .build();
    }

    /**
     * 函数式路由配置 - gRPC桥接处理器
     * 处理/api/grpc/**的所有请求
     *
     * @param handler gRPC桥接处理器
     * @return 路由函数
     */
    @Bean
    public RouterFunction<ServerResponse> grpcRouter(GrpcBridgeHandler handler) {
        return route()
                .POST("/api/grpc/{service}/{method}", handler::handleGrpcRequest)
                .GET("/api/grpc/user/{id}", handler::getUser)
                .GET("/api/grpc/order/{orderId}", handler::getOrder)
                .GET("/api/grpc/health", handler::checkHealth)
                .GET("/api/grpc/stats", handler::getStats)
                .build();
    }

    /**
     * 函数式路由配置 - 聚合处理器
     * 处理/api/aggregate/**的所有请求
     *
     * @param handler 聚合处理器
     * @return 路由函数
     */
    @Bean
    public RouterFunction<ServerResponse> aggregationRouter(AggregationHandler handler) {
        return route()
                .POST("/api/aggregate", handler::handleAggregation)
                .GET("/api/aggregate/user/{userId}", handler::getUserDetailAggregation)
                .GET("/api/aggregate/order/{orderId}", handler::getOrderDetailAggregation)
                .POST("/api/aggregate/custom", handler::handleCustomAggregation)
                .build();
    }
}

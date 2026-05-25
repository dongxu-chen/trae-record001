package com.apigateway.core.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 聚合请求数据传输对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AggregationRequest {

    /**
     * 要调用的服务列表
     */
    private List<ServiceCallConfig> services;

    /**
     * 全局超时配置（毫秒）
     */
    private Long timeout;

    /**
     * 是否忽略单个服务失败，继续返回其他结果
     */
    private Boolean ignoreFailures;

    /**
     * 服务调用配置
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceCallConfig {

        /**
         * 服务名称标识
         */
        private String name;

        /**
         * 服务类型：REST、GRPC、GRAPHQL
         */
        private String type;

        /**
         * 服务端点
         */
        private String endpoint;

        /**
         * HTTP方法（仅REST服务使用）
         */
        private String method;

        /**
         * 请求体
         */
        private Object body;

        /**
         * 单个服务超时时间（毫秒）
         */
        private Long timeout;

        /**
         * GraphQL变量（仅GRAPHQL服务使用）
         */
        private Map<String, Object> variables;

        /**
         * 请求头
         */
        private Map<String, String> headers;
    }
}

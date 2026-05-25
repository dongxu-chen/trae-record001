package com.apigateway.core.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 聚合响应数据传输对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AggregationResponse {

    /**
     * 聚合是否成功
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
     * 各服务的响应结果，key为服务名称
     */
    private Map<String, ServiceResult> results;

    /**
     * 聚合时间戳
     */
    private LocalDateTime timestamp;

    /**
     * 服务调用数量
     */
    private Integer serviceCount;

    /**
     * 成功调用的服务数量
     */
    private Integer successCount;

    /**
     * 失败调用的服务数量
     */
    private Integer failureCount;

    /**
     * 服务调用结果
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceResult {

        /**
         * 服务是否调用成功
         */
        private Boolean success;

        /**
         * 服务响应状态码
         */
        private Integer code;

        /**
         * 服务响应消息
         */
        private String message;

        /**
         * 服务响应数据
         */
        private Object data;

        /**
         * 错误信息（调用失败时）
         */
        private String error;

        /**
         * 服务响应时间（毫秒）
         */
        private Long responseTime;

        /**
         * 是否使用了降级结果
         */
        private Boolean fallback;
    }
}

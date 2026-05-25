package com.apigateway.core.health;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 探测结果实体
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthCheckResult {

    /**
     * 接口名称
     */
    private String endpointName;

    /**
     * 接口URL
     */
    private String url;

    /**
     * 实际响应状态码
     */
    private int statusCode;

    /**
     * 是否健康
     */
    private boolean healthy;

    /**
     * 响应时间（毫秒）
     */
    private long responseTime;

    /**
     * 错误信息（如果有）
     */
    private String errorMessage;

    /**
     * 探测时间
     */
    private LocalDateTime checkTime;
}

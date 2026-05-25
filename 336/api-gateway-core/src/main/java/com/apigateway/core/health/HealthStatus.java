package com.apigateway.core.health;

/**
 * 健康状态枚举
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
public enum HealthStatus {

    /**
     * 健康状态：所有接口正常
     */
    HEALTHY,

    /**
     * 降级状态：部分接口异常
     */
    DEGRADED,

    /**
     * 不健康状态：多数或全部接口异常
     */
    UNHEALTHY
}

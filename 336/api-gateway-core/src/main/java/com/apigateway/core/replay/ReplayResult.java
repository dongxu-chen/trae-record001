package com.apigateway.core.replay;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.Instant;

/**
 * 重放结果实体类
 * 存储请求重放后的结果信息，包括请求ID、目标环境、状态码、响应时间、响应体、错误信息等
 * 用于评估重放效果和对比不同环境的响应差异
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplayResult implements Serializable {

    /**
     * 重放结果唯一标识
     */
    private String resultId;

    /**
     * 原始请求ID
     */
    private String requestId;

    /**
     * 目标环境名称
     */
    private String targetEnvironment;

    /**
     * 目标环境URL
     */
    private String targetUrl;

    /**
     * HTTP响应状态码
     */
    private Integer statusCode;

    /**
     * 响应时间（毫秒）
     */
    private Long responseTime;

    /**
     * 响应体内容
     */
    private String responseBody;

    /**
     * 响应头（key为Header名，value为Header值）
     */
    private java.util.Map<String, String> responseHeaders;

    /**
     * 错误信息（重放失败时填充）
     */
    private String errorMessage;

    /**
     * 重放是否成功
     */
    private boolean success;

    /**
     * 重放执行时间
     */
    private Instant replayTime;

    /**
     * 原始响应状态码（用于对比）
     */
    private Integer originalStatusCode;

    /**
     * 状态码是否与原始响应一致
     */
    private boolean statusMatched;
}

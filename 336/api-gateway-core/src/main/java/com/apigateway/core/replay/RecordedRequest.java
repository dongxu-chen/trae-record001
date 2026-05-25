package com.apigateway.core.replay;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.Instant;
import java.util.Map;

/**
 * 录制请求实体类
 * 存储请求的完整信息，包括请求ID、方法、URL、路径、查询参数、Header、Body、时间戳、客户端IP等
 * 用于后续的请求重放和调试分析
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecordedRequest implements Serializable {

    /**
     * 请求唯一标识
     */
    private String requestId;

    /**
     * HTTP请求方法（GET、POST、PUT、DELETE等）
     */
    private String method;

    /**
     * 完整请求URL
     */
    private String url;

    /**
     * 请求路径
     */
    private String path;

    /**
     * 查询参数（key为参数名，value为参数值数组）
     */
    private Map<String, String[]> queryParams;

    /**
     * 请求头（key为Header名，value为Header值）
     */
    private Map<String, String> headers;

    /**
     * 请求体内容
     */
    private String body;

    /**
     * 请求录制时间戳
     */
    private Instant timestamp;

    /**
     * 客户端IP地址
     */
    private String clientIp;

    /**
     * 响应状态码（可选，用于记录原始响应）
     */
    private Integer responseStatus;

    /**
     * 请求耗时（毫秒，可选）
     */
    private Long duration;
}

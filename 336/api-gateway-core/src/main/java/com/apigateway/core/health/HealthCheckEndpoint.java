package com.apigateway.core.health;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.http.HttpMethod;

import java.time.Duration;

/**
 * 被探测的接口配置实体
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthCheckEndpoint {

    /**
     * 接口名称
     */
    @NotBlank(message = "接口名称不能为空")
    private String name;

    /**
     * 接口URL
     */
    @NotBlank(message = "接口URL不能为空")
    private String url;

    /**
     * HTTP请求方法
     */
    @NotNull(message = "请求方法不能为空")
    @Builder.Default
    private HttpMethod method = HttpMethod.GET;

    /**
     * 期望的HTTP状态码
     */
    @Builder.Default
    private int expectedStatusCode = 200;

    /**
     * 超时时间（毫秒）
     */
    @Builder.Default
    private Duration timeout = Duration.ofSeconds(5);

    /**
     * 探测频率（毫秒）
     */
    @Builder.Default
    private long checkInterval = 30000;

    /**
     * 是否启用该接口的探测
     */
    @Builder.Default
    private boolean enabled = true;
}

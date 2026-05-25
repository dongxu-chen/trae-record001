package com.apigateway.core.gray;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 灰度路由配置类
 * 配置灰度路由相关的属性和自动装配
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Configuration
@RequiredArgsConstructor
@EnableConfigurationProperties(GrayRouteProperties.class)
@ConditionalOnProperty(prefix = "gateway.gray", name = "enabled", havingValue = "true", matchIfMissing = false)
public class GrayRouteConfig {

    private final GrayRouteProperties properties;
}

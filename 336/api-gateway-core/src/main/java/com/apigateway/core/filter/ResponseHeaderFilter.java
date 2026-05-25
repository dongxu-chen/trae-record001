package com.apigateway.core.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * 响应头处理过滤器
 * 为所有响应添加安全相关的HTTP头，包括：
 * - X-Content-Type-Options: nosniff
 * - X-Frame-Options: DENY
 * - X-XSS-Protection: 1; mode=block
 * - Cache-Control: 缓存控制
 * 同时实现GatewayFilter（可针对特定路由）和GlobalFilter（全局生效）
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
public class ResponseHeaderFilter extends AbstractGatewayFilterFactory<ResponseHeaderFilter.Config>
        implements GlobalFilter, GatewayFilter, Ordered {

    /**
     * 过滤器配置类
     */
    public static class Config {
        private boolean enableSecurityHeaders = true;

        public boolean isEnableSecurityHeaders() {
            return enableSecurityHeaders;
        }

        public void setEnableSecurityHeaders(boolean enableSecurityHeaders) {
            this.enableSecurityHeaders = enableSecurityHeaders;
        }
    }

    public ResponseHeaderFilter() {
        super(Config.class);
    }

    /**
     * 过滤器执行顺序
     * 在请求处理完成后、响应返回前执行
     */
    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }

    /**
     * 全局过滤器实现
     * 对所有经过网关的请求生效
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return 响应式处理结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> addSecurityHeaders(exchange)));
    }

    /**
     * 网关过滤器工厂实现
     * 允许针对特定路由配置使用
     *
     * @param config 过滤器配置
     * @return 网关过滤器实例
     */
    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    if (config.isEnableSecurityHeaders()) {
                        addSecurityHeaders(exchange);
                    }
                }));
    }

    /**
     * 添加安全响应头
     *
     * @param exchange 服务器Web交换对象
     */
    private void addSecurityHeaders(ServerWebExchange exchange) {
        HttpHeaders headers = exchange.getResponse().getHeaders();

        headers.set("X-Content-Type-Options", "nosniff");
        headers.set("X-Frame-Options", "DENY");
        headers.set("X-XSS-Protection", "1; mode=block");
        headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
        headers.set("Pragma", "no-cache");
        headers.set("Expires", "0");
        headers.set("X-Gateway-Version", "1.0.0");

        log.debug("已添加安全响应头 - 路径: {}", exchange.getRequest().getURI().getPath());
    }
}

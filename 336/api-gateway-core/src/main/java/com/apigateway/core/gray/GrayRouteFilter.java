package com.apigateway.core.gray;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.route.Route;
import org.springframework.cloud.gateway.support.ServerWebExchangeUtils;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.time.Duration;
import java.time.Instant;

/**
 * 灰度路由全局过滤器
 * 实现GlobalFilter接口，根据灰度规则决定请求路由到v1还是v2版本
 * 支持响应式编程风格，使用Spring Cloud Gateway的过滤器链机制
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GrayRouteFilter implements GlobalFilter, Ordered {

    private final GrayRouteService grayRouteService;

    /**
     * 灰度路由过滤器执行顺序
     * 在路由确定之前执行，设置为较高优先级
     */
    private static final int GRAY_ROUTE_FILTER_ORDER = -100;

    /**
     * 灰度路由版本属性名，存储在Exchange中
     */
    public static final String GRAY_VERSION_ATTR = "grayVersion";

    /**
     * 灰度路由目标URI属性名
     */
    public static final String GRAY_TARGET_URI_ATTR = "grayTargetUri";

    /**
     * 灰度路由匹配规则ID属性名
     */
    public static final String GRAY_MATCHED_RULE_ID_ATTR = "grayMatchedRuleId";

    /**
     * 请求开始时间属性名
     */
    public static final String GRAY_REQUEST_START_TIME_ATTR = "grayRequestStartTime";

    /**
     * 灰度路由过滤方法
     * 根据灰度规则选择目标版本，动态修改路由URI
     *
     * @param exchange 服务器Web交换对象
     * @param chain    过滤器链
     * @return Mono<Void> 响应式结果
     */
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        // 记录请求开始时间
        exchange.getAttributes().put(GRAY_REQUEST_START_TIME_ATTR, Instant.now());

        // 选择路由版本
        GrayRouteService.RouteVersion routeVersion = grayRouteService.selectRouteVersion(exchange.getRequest());

        // 将版本信息存储到exchange中，便于后续使用
        exchange.getAttributes().put(GRAY_VERSION_ATTR, routeVersion.getVersion());
        exchange.getAttributes().put(GRAY_TARGET_URI_ATTR, routeVersion.getUri());
        exchange.getAttributes().put(GRAY_MATCHED_RULE_ID_ATTR, routeVersion.getMatchedRuleId());

        // 添加灰度相关响应头
        HttpHeaders headers = exchange.getResponse().getHeaders();
        headers.set("X-Gray-Version", routeVersion.getVersion());
        headers.set("X-Gray-Matched", String.valueOf(routeVersion.isMatched()));
        if (routeVersion.getMatchedRuleName() != null) {
            headers.set("X-Gray-Rule", routeVersion.getMatchedRuleName());
        }

        log.debug("灰度路由决策: 请求路径={}, 版本={}, 目标URI={}, 匹配规则={}",
                exchange.getRequest().getURI().getPath(),
                routeVersion.getVersion(),
                routeVersion.getUri(),
                routeVersion.getMatchedRuleName());

        // 动态修改路由URI
        modifyRouteUri(exchange, routeVersion);

        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    // 请求处理完成后记录统计
                    recordStats(exchange, routeVersion);
                }))
                .onErrorResume(e -> {
                    // 请求异常时也记录统计
                    recordStats(exchange, routeVersion, e);
                    return Mono.error(e);
                });
    }

    /**
     * 修改路由URI
     * 根据灰度路由结果动态修改目标服务地址
     *
     * @param exchange     服务器Web交换对象
     * @param routeVersion 路由版本信息
     */
    private void modifyRouteUri(ServerWebExchange exchange, GrayRouteService.RouteVersion routeVersion) {
        Route route = exchange.getAttribute(ServerWebExchangeUtils.GATEWAY_ROUTE_ATTR);
        if (route != null) {
            URI originalUri = route.getUri();
            URI newUri = URI.create(routeVersion.getUri());

            // 构建新的Route对象，保持其他属性不变
            Route newRoute = Route.async()
                    .id(route.getId())
                    .uri(newUri)
                    .order(route.getOrder())
                    .predicate(exchange1 -> true)
                    .asyncPredicate(route.getPredicate())
                    .filters(route.getFilters())
                    .metadata(route.getMetadata())
                    .build();

            exchange.getAttributes().put(ServerWebExchangeUtils.GATEWAY_ROUTE_ATTR, newRoute);

            // 同时更新GATEWAY_REQUEST_URL_ATTR
            URI requestUrl = exchange.getAttribute(ServerWebExchangeUtils.GATEWAY_REQUEST_URL_ATTR);
            if (requestUrl != null) {
                try {
                    URI newRequestUrl = new URI(
                            newUri.getScheme(),
                            newUri.getUserInfo(),
                            newUri.getHost(),
                            newUri.getPort(),
                            requestUrl.getPath(),
                            requestUrl.getQuery(),
                            requestUrl.getFragment()
                    );
                    exchange.getAttributes().put(ServerWebExchangeUtils.GATEWAY_REQUEST_URL_ATTR, newRequestUrl);
                } catch (Exception e) {
                    log.warn("更新请求URL失败: {}", e.getMessage());
                }
            }

            log.debug("路由已修改: 原URI={}, 新URI={}", originalUri, newUri);
        }
    }

    /**
     * 记录请求统计（成功）
     *
     * @param exchange     服务器Web交换对象
     * @param routeVersion 路由版本信息
     */
    private void recordStats(ServerWebExchange exchange, GrayRouteService.RouteVersion routeVersion) {
        try {
            HttpStatus status = exchange.getResponse().getStatusCode();
            boolean success = status != null && status.is2xxSuccessful();
            recordStats(exchange, routeVersion.getVersion(), success, null);
        } catch (Exception e) {
            log.warn("记录灰度统计失败: {}", e.getMessage());
        }
    }

    /**
     * 记录请求统计（异常）
     *
     * @param exchange     服务器Web交换对象
     * @param routeVersion 路由版本信息
     * @param e            异常信息
     */
    private void recordStats(ServerWebExchange exchange, GrayRouteService.RouteVersion routeVersion, Throwable e) {
        try {
            recordStats(exchange, routeVersion.getVersion(), false, e);
        } catch (Exception ex) {
            log.warn("记录灰度统计（异常）失败: {}", ex.getMessage());
        }
    }

    /**
     * 记录请求统计（内部方法）
     *
     * @param exchange 服务器Web交换对象
     * @param version  版本
     * @param success  是否成功
     * @param e        异常信息（可为null）
     */
    private void recordStats(ServerWebExchange exchange, String version, boolean success, Throwable e) {
        Instant startTime = exchange.getAttribute(GRAY_REQUEST_START_TIME_ATTR);
        long latency = 0;
        if (startTime != null) {
            latency = Duration.between(startTime, Instant.now()).toMillis();
        }

        grayRouteService.recordRequest(version, latency, success);

        if (e != null) {
            log.debug("灰度路由请求异常: 版本={}, 路径={}, 延迟={}ms, 错误={}",
                    version, exchange.getRequest().getURI().getPath(), latency, e.getMessage());
        } else {
            log.debug("灰度路由请求完成: 版本={}, 路径={}, 延迟={}ms, 成功={}",
                    version, exchange.getRequest().getURI().getPath(), latency, success);
        }
    }

    /**
     * 获取过滤器执行顺序
     *
     * @return 顺序值，值越小越先执行
     */
    @Override
    public int getOrder() {
        return GRAY_ROUTE_FILTER_ORDER;
    }
}

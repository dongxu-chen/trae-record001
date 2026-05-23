package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.route.Route;
import org.springframework.cloud.gateway.support.ServerWebExchangeUtils;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class GrayReleaseFilter implements GlobalFilter, Ordered {

    private final GatewayProperties gatewayProperties;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!gatewayProperties.getGrayRelease().isEnabled()) {
            return chain.filter(exchange);
        }

        String versionHeader = gatewayProperties.getGrayRelease().getVersionHeader();
        String version = exchange.getRequest().getHeaders().getFirst(versionHeader);

        if (version == null || version.isEmpty()) {
            return chain.filter(exchange);
        }

        Route route = exchange.getAttribute(ServerWebExchangeUtils.GATEWAY_ROUTE_ATTR);
        if (route == null) {
            return chain.filter(exchange);
        }

        String serviceId = route.getId();
        Map<String, String> versionRoutes = gatewayProperties.getGrayRelease().getVersionRoutes();

        String routeKey = serviceId + "-" + version;
        String targetUri = versionRoutes.get(routeKey);

        if (targetUri == null) {
            log.debug("No gray route found for service={}, version={}, using default", serviceId, version);
            return chain.filter(exchange);
        }

        URI originalUri = route.getUri();
        URI newUri = URI.create(targetUri);

        log.info("Gray release: service={}, version={}, {} -> {}", serviceId, version, originalUri, newUri);

        exchange.getAttributes().put(ServerWebExchangeUtils.GATEWAY_REQUEST_URL_ATTR, newUri);
        exchange.getAttributes().put("grayVersion", version);
        exchange.getAttributes().put("grayOriginalUri", originalUri);

        exchange.getResponse().getHeaders().add("X-Gray-Version", version);

        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        return -40;
    }
}

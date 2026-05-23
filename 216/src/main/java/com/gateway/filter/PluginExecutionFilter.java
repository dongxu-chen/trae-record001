package com.gateway.filter;

import com.gateway.plugin.PluginManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@Component
@RequiredArgsConstructor
public class PluginExecutionFilter implements GlobalFilter, Ordered {

    private final PluginManager pluginManager;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (pluginManager.getPlugins().isEmpty()) {
            return chain.filter(exchange);
        }

        log.debug("Starting plugin execution chain for path: {}",
                exchange.getRequest().getURI().getPath());

        return pluginManager.createChain(() -> {})
                .doFilter(exchange)
                .then(Mono.defer(() -> {
                    log.debug("Plugin chain completed, proceeding to route");
                    return chain.filter(exchange);
                }));
    }

    @Override
    public int getOrder() {
        return -80;
    }
}

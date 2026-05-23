package com.gateway.plugin;

import lombok.extern.slf4j.Slf4j;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
public class DefaultPluginChain implements PluginChain {

    private final List<GatewayPlugin> plugins;
    private final AtomicInteger index = new AtomicInteger(0);
    private final Runnable chainCompleteHandler;

    public DefaultPluginChain(List<GatewayPlugin> plugins, Runnable chainCompleteHandler) {
        this.plugins = plugins;
        this.chainCompleteHandler = chainCompleteHandler;
    }

    @Override
    public Mono<Void> doFilter(ServerWebExchange exchange) {
        if (index.get() >= plugins.size()) {
            if (chainCompleteHandler != null) {
                chainCompleteHandler.run();
            }
            return Mono.empty();
        }

        GatewayPlugin plugin = plugins.get(index.getAndIncrement());

        if (!plugin.isEnabled()) {
            log.debug("Plugin [{}] is disabled, skipping", plugin.getName());
            return doFilter(exchange);
        }

        log.debug("Executing plugin [{}] at index {}", plugin.getName(), index.get() - 1);

        return plugin.execute(exchange, this)
                .doOnError(e -> log.error("Error executing plugin [{}]", plugin.getName(), e));
    }

    public void reset() {
        index.set(0);
    }
}

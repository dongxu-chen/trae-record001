package com.gateway.plugin;

import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

public interface GatewayPlugin {

    Mono<Void> execute(ServerWebExchange exchange, PluginChain chain);

    default int getOrder() {
        return 0;
    }

    default boolean isEnabled() {
        return true;
    }

    default String getName() {
        return this.getClass().getSimpleName();
    }
}

package com.gateway.plugin;

import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

public interface PluginChain {

    Mono<Void> doFilter(ServerWebExchange exchange);
}

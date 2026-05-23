package com.gateway.plugin.impl;

import com.gateway.plugin.GatewayPlugin;
import com.gateway.plugin.PluginChain;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.UUID;

@Slf4j
@Component
public class RequestEnhancerPlugin implements GatewayPlugin {

    @Override
    public Mono<Void> execute(ServerWebExchange exchange, PluginChain chain) {
        log.debug("Executing RequestEnhancerPlugin");

        ServerHttpRequest originalRequest = exchange.getRequest();

        String requestId = originalRequest.getHeaders().getFirst("X-Request-Id");
        if (requestId == null || requestId.isEmpty()) {
            requestId = UUID.randomUUID().toString();
        }

        String timestamp = String.valueOf(Instant.now().toEpochMilli());

        ServerHttpRequest enhancedRequest = originalRequest.mutate()
                .header("X-Request-Id", requestId)
                .header("X-Gateway-Timestamp", timestamp)
                .header("X-Gateway-Received", "true")
                .build();

        exchange.getAttributes().put("requestId", requestId);

        return chain.doFilter(exchange.mutate().request(enhancedRequest).build());
    }

    @Override
    public int getOrder() {
        return 10;
    }

    @Override
    public String getName() {
        return "RequestEnhancerPlugin";
    }
}

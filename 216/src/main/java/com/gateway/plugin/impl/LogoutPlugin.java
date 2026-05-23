package com.gateway.plugin.impl;

import com.gateway.plugin.GatewayPlugin;
import com.gateway.plugin.PluginChain;
import com.gateway.service.JwtBlacklistService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@Component
@RequiredArgsConstructor
public class LogoutPlugin implements GatewayPlugin {

    private final JwtBlacklistService jwtBlacklistService;

    @Override
    public Mono<Void> execute(ServerWebExchange exchange, PluginChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        HttpMethod method = request.getMethod();

        if ("/api/auth/logout".equals(path) && HttpMethod.POST.equals(method)) {
            String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                exchange.getResponse().setStatusCode(HttpStatus.BAD_REQUEST);
                return exchange.getResponse().setComplete();
            }

            String token = authHeader.substring(7);

            return jwtBlacklistService.blacklistToken(token)
                    .flatMap(success -> {
                        if (success) {
                            log.info("User logged out successfully");
                            exchange.getResponse().setStatusCode(HttpStatus.OK);
                        } else {
                            exchange.getResponse().setStatusCode(HttpStatus.BAD_REQUEST);
                        }
                        return exchange.getResponse().setComplete();
                    });
        }

        return chain.doFilter(exchange);
    }

    @Override
    public int getOrder() {
        return 5;
    }

    @Override
    public String getName() {
        return "LogoutPlugin";
    }
}

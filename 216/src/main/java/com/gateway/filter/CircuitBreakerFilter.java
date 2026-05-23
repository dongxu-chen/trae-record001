package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerOpenException;
import io.github.resilience4j.reactor.circuitbreaker.operator.CircuitBreakerOperator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.route.Route;
import org.springframework.cloud.gateway.support.ServerWebExchangeUtils;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class CircuitBreakerFilter implements GlobalFilter, Ordered {

    private final Map<String, CircuitBreaker> circuitBreakerMap;
    private final GatewayProperties gatewayProperties;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!gatewayProperties.getCircuitBreaker().isEnabled()) {
            return chain.filter(exchange);
        }

        Route route = exchange.getAttribute(ServerWebExchangeUtils.GATEWAY_ROUTE_ATTR);
        if (route == null) {
            return chain.filter(exchange);
        }

        String serviceId = route.getId();
        CircuitBreaker circuitBreaker = circuitBreakerMap.get(serviceId);

        if (circuitBreaker == null) {
            log.debug("No circuit breaker configured for service: {}", serviceId);
            return chain.filter(exchange);
        }

        log.debug("Circuit breaker [{}] state: {}", serviceId, circuitBreaker.getState());

        return chain.filter(exchange)
                .transformDeferred(CircuitBreakerOperator.of(circuitBreaker))
                .onErrorResume(CircuitBreakerOpenException.class, e -> {
                    log.warn("Circuit breaker OPEN for service: {}, returning fallback", serviceId);
                    exchange.getResponse().setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);
                    exchange.getResponse().getHeaders().add("X-Circuit-Breaker", serviceId);
                    exchange.getResponse().getHeaders().add("X-Circuit-Breaker-State", "OPEN");
                    return exchange.getResponse().setComplete();
                })
                .onErrorResume(Exception.class, e -> {
                    if (!(e instanceof CircuitBreakerOpenException)) {
                        log.error("Service [{}] call failed: {}", serviceId, e.getMessage());
                        exchange.getResponse().setStatusCode(HttpStatus.BAD_GATEWAY);
                        return exchange.getResponse().setComplete();
                    }
                    return Mono.error(e);
                });
    }

    @Override
    public int getOrder() {
        return -30;
    }
}

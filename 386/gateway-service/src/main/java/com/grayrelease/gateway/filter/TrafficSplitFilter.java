package com.grayrelease.gateway.filter;

import com.grayrelease.gateway.registry.TrafficRoutingRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.Random;

@Slf4j
@Component
@RequiredArgsConstructor
public class TrafficSplitFilter implements GlobalFilter, Ordered {

    private final TrafficRoutingRegistry routingRegistry;
    private final Random random = new Random();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String serviceName = extractServiceName(exchange);
        TrafficRoutingRegistry.RoutingConfig config = routingRegistry.getRouting(serviceName);

        if (config == null || config.getCanaryWeight() <= 0) {
            return chain.filter(exchange);
        }

        if (shouldRouteToCanary(config, exchange)) {
            String canaryHost = config.getCanaryHost();
            log.debug("Routing to canary: service={}, version={}, host={}",
                    serviceName, config.getCanaryVersion(), canaryHost);

            exchange.getRequest().mutate()
                    .header("X-Gray-Release-Version", config.getCanaryVersion())
                    .header("X-Gray-Release-Routed", "canary")
                    .build();

            exchange.getAttributes().put("grayRelease.targetHost", canaryHost);
            exchange.getAttributes().put("grayRelease.targetPort", config.getCanaryPort());
        } else {
            exchange.getRequest().mutate()
                    .header("X-Gray-Release-Version", config.getStableVersion())
                    .header("X-Gray-Release-Routed", "stable")
                    .build();
        }

        return chain.filter(exchange);
    }

    private boolean shouldRouteToCanary(TrafficRoutingRegistry.RoutingConfig config, ServerWebExchange exchange) {
        Map<String, String> matchRules = config.getMatchRules();
        if (matchRules != null && !matchRules.isEmpty()) {
            return matchByRules(matchRules, exchange);
        }

        int randomValue = random.nextInt(100) + 1;
        return randomValue <= config.getCanaryWeight();
    }

    private boolean matchByRules(Map<String, String> matchRules, ServerWebExchange exchange) {
        HttpHeaders headers = exchange.getRequest().getHeaders();
        for (Map.Entry<String, String> rule : matchRules.entrySet()) {
            String headerName = rule.getKey();
            String expectedValue = rule.getValue();
            String actualValue = headers.getFirst(headerName);

            if (expectedValue.equals(actualValue)) {
                return true;
            }
        }
        return false;
    }

    private String extractServiceName(ServerWebExchange exchange) {
        String path = exchange.getRequest().getPath().value();
        String[] segments = path.split("/");
        if (segments.length > 1) {
            return segments[1];
        }
        return "default";
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
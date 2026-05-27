package com.grayrelease.gateway.filter;

import io.prometheus.client.Counter;
import io.prometheus.client.Histogram;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@Component
public class MetricsFilter implements GlobalFilter, Ordered {

    private static final Counter requestCounter = Counter.build()
            .name("gray_release_requests_total")
            .help("Total requests processed by gray release gateway")
            .labelNames("service", "version", "routed")
            .register();

    private static final Histogram requestLatency = Histogram.build()
            .name("gray_release_request_duration_seconds")
            .help("Request duration in seconds")
            .labelNames("service", "version")
            .register();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        long startTime = System.currentTimeMillis();

        String version = exchange.getRequest().getHeaders().getFirst("X-Gray-Release-Version");
        String routed = exchange.getRequest().getHeaders().getFirst("X-Gray-Release-Routed");
        String serviceName = extractServiceName(exchange);

        requestCounter.labels(serviceName, version != null ? version : "unknown",
                routed != null ? routed : "direct").inc();

        return chain.filter(exchange).then(Mono.fromRunnable(() -> {
            long duration = System.currentTimeMillis() - startTime;
            requestLatency.labels(serviceName, version != null ? version : "unknown")
                    .observe(duration / 1000.0);
        }));
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
        return -50;
    }
}
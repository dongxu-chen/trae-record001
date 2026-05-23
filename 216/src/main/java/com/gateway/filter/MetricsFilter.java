package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
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

import java.time.Duration;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class MetricsFilter implements GlobalFilter, Ordered {

    private final MeterRegistry meterRegistry;
    private final GatewayProperties gatewayProperties;

    private final ConcurrentHashMap<String, Timer> timerCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> counterCache = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> errorCounterCache = new ConcurrentHashMap<>();

    private static final String METRICS_PREFIX = "gateway";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!gatewayProperties.getMetrics().isEnabled()) {
            return chain.filter(exchange);
        }

        String path = exchange.getRequest().getURI().getPath();
        String method = exchange.getRequest().getMethod() != null
                ? exchange.getRequest().getMethod().name()
                : "UNKNOWN";

        Route route = exchange.getAttribute(ServerWebExchangeUtils.GATEWAY_ROUTE_ATTR);
        String serviceId = route != null ? route.getId() : "unknown";

        String version = exchange.getAttribute("grayVersion");
        version = version != null ? version : "default";

        String baseKey = serviceId + ":" + method + ":" + normalizePath(path);

        Timer.Sample sample = Timer.start(meterRegistry);
        long startTime = System.currentTimeMillis();

        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    long duration = System.currentTimeMillis() - startTime;
                    int status = exchange.getResponse().getStatusCode() != null
                            ? exchange.getResponse().getStatusCode().value()
                            : 0;

                    recordMetrics(baseKey, serviceId, method, path, version, status, duration, sample);
                }))
                .onErrorResume(e -> {
                    long duration = System.currentTimeMillis() - startTime;
                    recordMetrics(baseKey, serviceId, method, path, version, 500, duration, sample);
                    return Mono.error(e);
                });
    }

    private void recordMetrics(String baseKey, String serviceId, String method, String path,
                                String version, int status, long duration, Timer.Sample sample) {
        try {
            boolean isError = status >= 400;

            String timerKey = baseKey + ":" + status;
            Timer timer = timerCache.computeIfAbsent(timerKey, k -> Timer.builder(METRICS_PREFIX + "_request_latency")
                    .description("Request latency")
                    .tag("service", serviceId)
                    .tag("method", method)
                    .tag("path", normalizePath(path))
                    .tag("version", version)
                    .tag("status", String.valueOf(status))
                    .register(meterRegistry));

            if (sample != null) {
                sample.stop(timer);
            }

            String counterKey = baseKey + ":total";
            Counter counter = counterCache.computeIfAbsent(counterKey, k -> Counter.builder(METRICS_PREFIX + "_request_total")
                    .description("Total requests")
                    .tag("service", serviceId)
                    .tag("method", method)
                    .tag("path", normalizePath(path))
                    .tag("version", version)
                    .register(meterRegistry));
            counter.increment();

            if (isError) {
                String errorKey = baseKey + ":error";
                Counter errorCounter = errorCounterCache.computeIfAbsent(errorKey, k ->
                        Counter.builder(METRICS_PREFIX + "_request_error")
                                .description("Error requests")
                                .tag("service", serviceId)
                                .tag("method", method)
                                .tag("path", normalizePath(path))
                                .tag("version", version)
                                .tag("status", String.valueOf(status))
                                .register(meterRegistry));
                errorCounter.increment();
            }

            log.debug("Metrics: service={}, method={}, path={}, status={}, duration={}ms, error={}",
                    serviceId, method, path, status, duration, isError);

        } catch (Exception e) {
            log.warn("Failed to record metrics", e);
        }
    }

    private String normalizePath(String path) {
        if (path == null) {
            return "unknown";
        }
        String[] segments = path.split("/");
        StringBuilder normalized = new StringBuilder();
        for (String segment : segments) {
            if (segment.matches("^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$")) {
                normalized.append("/{uuid}");
            } else if (segment.matches("^\\d+$")) {
                normalized.append("/{id}");
            } else if (!segment.isEmpty()) {
                normalized.append("/").append(segment);
            }
        }
        return normalized.length() == 0 ? "/" : normalized.toString();
    }

    @Override
    public int getOrder() {
        return -200;
    }
}

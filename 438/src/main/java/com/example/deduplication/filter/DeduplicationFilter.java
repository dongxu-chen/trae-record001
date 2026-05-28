package com.example.deduplication.filter;

import com.example.deduplication.core.DeduplicationService;
import com.example.deduplication.model.CachedResponse;
import com.example.deduplication.model.DeduplicationResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@Component
@RequiredArgsConstructor
public class DeduplicationFilter implements GlobalFilter, Ordered {

    private static final int ORDER = -100;
    private static final String X_DEDUPLICATED = "X-Deduplicated";
    private static final String X_REQUEST_HASH = "X-Request-Hash";
    private static final String X_BYPASS_VALIDATION = "X-Bypass-Validation";
    private static final String X_FINGERPRINT = "X-Request-Fingerprint";

    private final DeduplicationService deduplicationService;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();

        if (!requiresDeduplication(request)) {
            return chain.filter(exchange);
        }

        CachingBodyDecorator decorator = new CachingBodyDecorator(request);

        return decorator.getCachedBody()
                .flatMap(body -> deduplicationService.checkDuplicate(decorator, body))
                .flatMap(result -> {
                    if (result.isBypassValidation()) {
                        return handleBypassValidation(exchange, chain, decorator, result);
                    }

                    if (result.isDuplicate() && result.getCachedResponse() != null) {
                        log.info("Returning cached response for hash: {}", result.getRequestHash());
                        return writeCachedResponse(exchange, result);
                    }

                    return handleNormalRequest(exchange, chain, decorator, result);
                });
    }

    private Mono<Void> handleBypassValidation(ServerWebExchange exchange, GatewayFilterChain chain,
                                               CachingBodyDecorator decorator, DeduplicationResult result) {
        log.info("Performing bypass validation for hash: {}", result.getRequestHash());

        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(decorator)
                .build();

        CachingResponseDecorator responseDecorator = new CachingResponseDecorator(
                mutatedExchange.getResponse());

        ServerWebExchange exchangeWithResponseDecorator = mutatedExchange.mutate()
                .response(responseDecorator)
                .build();

        exchangeWithResponseDecorator.getResponse().getHeaders().add(X_BYPASS_VALIDATION, "true");

        return chain.filter(exchangeWithResponseDecorator)
                .doOnSuccess(aVoid -> {
                    CachedResponse actualResponse = CachedResponse.builder()
                            .status(responseDecorator.getCachedStatus())
                            .headers(responseDecorator.getCachedHeaders())
                            .body(responseDecorator.getCachedBody())
                            .build();

                    deduplicationService.cacheResponse(result.getRequestHash(), actualResponse);
                    deduplicationService.performValidation(result.getRequestHash(), null, actualResponse);
                })
                .doOnError(error -> {
                    log.error("Bypass validation request failed", error);
                });
    }

    private Mono<Void> handleNormalRequest(ServerWebExchange exchange, GatewayFilterChain chain,
                                            CachingBodyDecorator decorator, DeduplicationResult result) {
        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(decorator)
                .build();

        if (result.getFingerprint() != null) {
            mutatedExchange.getResponse().getHeaders().add(X_FINGERPRINT, result.getFingerprint());
        }

        CachingResponseDecorator responseDecorator = new CachingResponseDecorator(
                mutatedExchange.getResponse());

        ServerWebExchange exchangeWithResponseDecorator = mutatedExchange.mutate()
                .response(responseDecorator)
                .build();

        return chain.filter(exchangeWithResponseDecorator)
                .doOnSuccess(aVoid -> {
                    CachedResponse cachedResponse = CachedResponse.builder()
                            .status(responseDecorator.getCachedStatus())
                            .headers(responseDecorator.getCachedHeaders())
                            .body(responseDecorator.getCachedBody())
                            .build();
                    deduplicationService.cacheResponse(result.getRequestHash(), cachedResponse);
                    deduplicationService.releaseLock(result.getRequestHash());
                })
                .doOnError(error -> {
                    log.error("Request processing failed, releasing lock", error);
                    deduplicationService.releaseLock(result.getRequestHash());
                });
    }

    private Mono<Void> writeCachedResponse(ServerWebExchange exchange, DeduplicationResult result) {
        ServerHttpResponse response = exchange.getResponse();
        CachedResponse cached = result.getCachedResponse();

        response.setStatusCode(HttpStatus.valueOf(cached.getStatus()));
        response.getHeaders().add(X_DEDUPLICATED, "true");
        response.getHeaders().add(X_REQUEST_HASH, result.getRequestHash());

        if (result.getFingerprint() != null) {
            response.getHeaders().add(X_FINGERPRINT, result.getFingerprint());
        }

        if (cached.getHeaders() != null) {
            cached.getHeaders().forEach((key, value) -> {
                if (!response.getHeaders().containsKey(key)) {
                    response.getHeaders().add(key, value);
                }
            });
        }

        String body = cached.getBody() != null ? cached.getBody() : "";
        byte[] bytes = body.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        response.getHeaders().setContentLength(bytes.length);

        if (!response.getHeaders().containsKey(HttpHeaders.CONTENT_TYPE)) {
            response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        }

        org.springframework.core.io.buffer.DataBufferFactory bufferFactory = response.bufferFactory();
        org.springframework.core.io.buffer.DataBuffer buffer = bufferFactory.wrap(bytes);

        return response.writeWith(Mono.just(buffer));
    }

    private boolean requiresDeduplication(ServerHttpRequest request) {
        String method = request.getMethod().name();
        return "POST".equals(method) || "PUT".equals(method);
    }

    @Override
    public int getOrder() {
        return ORDER;
    }
}

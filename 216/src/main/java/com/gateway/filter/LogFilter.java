package com.gateway.filter;

import com.gateway.config.GatewayProperties;
import com.gateway.util.DataMaskUtil;
import com.gateway.wrapper.CachedBodyHttpRequest;
import com.gateway.wrapper.CachedBodyHttpResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.time.Instant;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class LogFilter implements GlobalFilter, Ordered {

    private final DataMaskUtil dataMaskUtil;
    private final GatewayProperties gatewayProperties;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!gatewayProperties.getLog().isEnabled()) {
            return chain.filter(exchange);
        }

        ServerHttpRequest request = exchange.getRequest();
        URI uri = request.getURI();
        HttpMethod method = request.getMethod();
        String path = uri.getPath();
        String userId = exchange.getAttribute("userId");
        String traceId = exchange.getRequest().getHeaders().getFirst("X-Trace-Id");
        if (traceId == null) {
            traceId = java.util.UUID.randomUUID().toString();
        }

        long startTime = Instant.now().toEpochMilli();

        exchange.getAttributes().put("traceId", traceId);
        exchange.getAttributes().put("startTime", startTime);

        MediaType contentType = request.getHeaders().getContentType();
        boolean shouldLogBody = shouldLogBody(contentType);

        if (shouldLogBody) {
            return DataBufferUtils.join(request.getBody())
                    .map(dataBuffer -> {
                        byte[] bytes = new byte[dataBuffer.readableByteCount()];
                        dataBuffer.read(bytes);
                        DataBufferUtils.release(dataBuffer);
                        return bytes;
                    })
                    .defaultIfEmpty(new byte[0])
                    .flatMap(bytes -> {
                        CachedBodyHttpRequest cachedRequest = new CachedBodyHttpRequest(request, bytes);
                        String rawBody = cachedRequest.getCachedBody();
                        String maskedBody = maskBody(rawBody);

                        logRequest(method, path, userId, traceId, maskedBody, request);

                        CachedBodyHttpResponse cachedResponse = new CachedBodyHttpResponse(exchange.getResponse());

                        return chain.filter(exchange.mutate()
                                        .request(cachedRequest)
                                        .response(cachedResponse)
                                        .build())
                                .then(Mono.fromRunnable(() ->
                                        logResponse(cachedResponse, method, path, userId, traceId, startTime)));
                    });
        } else {
            logRequest(method, path, userId, traceId, null, request);

            CachedBodyHttpResponse cachedResponse = new CachedBodyHttpResponse(exchange.getResponse());

            return chain.filter(exchange.mutate()
                            .response(cachedResponse)
                            .build())
                    .then(Mono.fromRunnable(() ->
                            logResponse(cachedResponse, method, path, userId, traceId, startTime)));
        }
    }

    private boolean shouldLogBody(MediaType contentType) {
        if (contentType == null) {
            return false;
        }
        return contentType.isCompatibleWith(MediaType.APPLICATION_JSON)
                || contentType.isCompatibleWith(MediaType.APPLICATION_FORM_URLENCODED);
    }

    private String maskBody(String body) {
        List<String> maskFields = gatewayProperties.getLog().getMaskFields();
        int maxSize = gatewayProperties.getLog().getMaxBodySize();

        if (body.length() > maxSize) {
            body = body.substring(0, maxSize) + "... [truncated]";
        }

        return dataMaskUtil.maskBody(body, maskFields);
    }

    private void logRequest(HttpMethod method, String path, String userId, String traceId,
                            String body, ServerHttpRequest request) {
        StringBuilder logMsg = new StringBuilder();
        logMsg.append("[REQUEST] ");
        logMsg.append("traceId=").append(traceId).append(", ");
        logMsg.append("userId=").append(userId != null ? userId : "anonymous").append(", ");
        logMsg.append("method=").append(method).append(", ");
        logMsg.append("path=").append(path).append(", ");
        logMsg.append("clientIp=").append(getClientIp(request)).append(", ");
        logMsg.append("userAgent=").append(request.getHeaders().getFirst("User-Agent"));

        if (body != null && !body.isEmpty()) {
            logMsg.append(", body=").append(body);
        }

        log.info(logMsg.toString());
    }

    private void logResponse(CachedBodyHttpResponse response, HttpMethod method, String path,
                             String userId, String traceId, long startTime) {
        long duration = Instant.now().toEpochMilli() - startTime;
        int status = response.getStatusCode() != null ? response.getStatusCode().value() : 0;
        String rawBody = response.getCachedBody();
        String maskedBody = maskBody(rawBody);

        StringBuilder logMsg = new StringBuilder();
        logMsg.append("[RESPONSE] ");
        logMsg.append("traceId=").append(traceId).append(", ");
        logMsg.append("userId=").append(userId != null ? userId : "anonymous").append(", ");
        logMsg.append("method=").append(method).append(", ");
        logMsg.append("path=").append(path).append(", ");
        logMsg.append("status=").append(status).append(", ");
        logMsg.append("duration=").append(duration).append("ms");

        if (maskedBody != null && !maskedBody.isEmpty()) {
            logMsg.append(", body=").append(maskedBody);
        }

        if (status >= 400 && status < 500) {
            log.warn(logMsg.toString());
        } else if (status >= 500) {
            log.error(logMsg.toString());
        } else {
            log.info(logMsg.toString());
        }
    }

    private String getClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }

        String xRealIp = request.getHeaders().getFirst("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }

        return request.getRemoteAddress() != null
                ? request.getRemoteAddress().getAddress().getHostAddress()
                : "unknown";
    }

    @Override
    public int getOrder() {
        return -1000;
    }
}

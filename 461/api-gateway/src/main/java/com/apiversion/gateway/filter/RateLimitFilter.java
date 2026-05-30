package com.apiversion.gateway.filter;

import com.apiversion.gateway.config.RateLimitConfig;
import com.apiversion.gateway.ratelimit.BatchPushManager;
import com.apiversion.gateway.ratelimit.TokenBucketRateLimiter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class RateLimitFilter implements GlobalFilter, Ordered {

    private final RateLimitConfig rateLimitConfig;
    private final BatchPushManager batchPushManager;

    private static final String USER_ID_HEADER = "X-User-Id";
    private static final String CLIENT_VERSION_HEADER = "X-Client-Version";
    private static final String RATE_LIMIT_REMAINING = "X-RateLimit-Remaining";
    private static final String RATE_LIMIT_LIMIT = "X-RateLimit-Limit";
    private static final String BATCH_PUSH_HEADER = "X-Batch-Push";

    private final Map<String, TokenBucketRateLimiter> rateLimiters = new ConcurrentHashMap<>();

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!rateLimitConfig.isEnabled()) {
            return chain.filter(exchange);
        }

        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        String userId = request.getHeaders().getFirst(USER_ID_HEADER);
        String clientVersion = request.getHeaders().getFirst(CLIENT_VERSION_HEADER);

        TokenBucketRateLimiter rateLimiter = getOrCreateRateLimiter(path);

        if (!rateLimiter.tryAcquire()) {
            log.warn("请求被限流: path={}, userId={}", path, userId);
            return handleRateLimitExceeded(exchange, rateLimiter);
        }

        return batchPushManager.processBatchPush(path, userId, clientVersion)
                .flatMap(batchResult -> {
                    if (!batchResult.isAllowed()) {
                        log.debug("分批推送拦截: path={}, userId={}, message={}",
                                path, userId, batchResult.getMessage());
                        return handleBatchPushBlocked(exchange, batchResult);
                    }

                    addRateLimitHeaders(exchange, rateLimiter, batchResult);

                    if (log.isDebugEnabled()) {
                        log.debug("请求通过限流检查: path={}, userId={}, " +
                                        "availableTokens={}, batch={}/{}",
                                path, userId, rateLimiter.getAvailableTokens(),
                                batchResult.getCurrentBatch(), batchResult.getTotalBatches());
                    }

                    return chain.filter(exchange);
                });
    }

    private TokenBucketRateLimiter getOrCreateRateLimiter(String path) {
        return rateLimiters.computeIfAbsent(path, k -> new TokenBucketRateLimiter(
                rateLimitConfig.getMaxRequestsPerSecond(),
                rateLimitConfig.getBurstCapacity(),
                rateLimitConfig.getWarmUpPeriodSec()
        ));
    }

    private Mono<Void> handleRateLimitExceeded(ServerWebExchange exchange, TokenBucketRateLimiter rateLimiter) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
        response.getHeaders().add(RATE_LIMIT_LIMIT, String.valueOf(rateLimitConfig.getMaxRequestsPerSecond()));
        response.getHeaders().add(RATE_LIMIT_REMAINING, "0");
        response.getHeaders().add("Retry-After", "1");

        String message = String.format("请求过于频繁，请稍后再试。限制: %d请求/秒",
                rateLimitConfig.getMaxRequestsPerSecond());
        byte[] bytes = message.getBytes();

        return response.writeWith(Mono.just(response.bufferFactory().wrap(bytes)));
    }

    private Mono<Void> handleBatchPushBlocked(ServerWebExchange exchange, BatchPushManager.BatchPushResult batchResult) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);
        response.getHeaders().add(BATCH_PUSH_HEADER, "blocked");
        response.getHeaders().add("X-Batch-Current", String.valueOf(batchResult.getCurrentBatch()));
        response.getHeaders().add("X-Batch-Total", String.valueOf(batchResult.getTotalBatches()));

        String message = String.format("分批推送中，%s", batchResult.getMessage());
        byte[] bytes = message.getBytes();

        return response.writeWith(Mono.just(response.bufferFactory().wrap(bytes)));
    }

    private void addRateLimitHeaders(ServerWebExchange exchange, TokenBucketRateLimiter rateLimiter,
                                     BatchPushManager.BatchPushResult batchResult) {
        ServerHttpResponse response = exchange.getResponse();
        response.getHeaders().add(RATE_LIMIT_LIMIT, String.valueOf(rateLimitConfig.getMaxRequestsPerSecond()));
        response.getHeaders().add(RATE_LIMIT_REMAINING, String.valueOf(rateLimiter.getAvailableTokens()));
        response.getHeaders().add(BATCH_PUSH_HEADER, String.valueOf(batchResult.isAllowed()));
        response.getHeaders().add("X-Batch-Current", String.valueOf(batchResult.getCurrentBatch()));
        response.getHeaders().add("X-Batch-Total", String.valueOf(batchResult.getTotalBatches()));
    }

    @Override
    public int getOrder() {
        return -70;
    }
}

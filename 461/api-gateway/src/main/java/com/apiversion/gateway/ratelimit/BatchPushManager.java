package com.apiversion.gateway.ratelimit;

import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
@RequiredArgsConstructor
public class BatchPushManager {

    private final ReactiveStringRedisTemplate redisTemplate;

    private static final String BATCH_PUSH_KEY_PREFIX = "api:batch:push:";
    private static final String BATCH_PROGRESS_KEY_PREFIX = "api:batch:progress:";

    private final Map<String, BatchPushContext> pushContexts = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        log.info("分批推送管理器已初始化");
    }

    public Mono<BatchPushResult> processBatchPush(String apiPath, String userId, String clientVersion) {
        BatchPushContext context = getOrCreateContext(apiPath);
        BatchConfig config = context.getConfig();

        return getCurrentBatchNumber(apiPath)
                .flatMap(batchNumber -> {
                    if (batchNumber <= 0) {
                        return Mono.just(new BatchPushResult(false, "推送未开始", 0, 0));
                    }

                    return isUserInBatch(apiPath, userId, batchNumber, config)
                            .flatMap(inBatch -> {
                                if (!inBatch) {
                                    return Mono.just(new BatchPushResult(false,
                                            "用户不在当前批次中，当前批次: " + batchNumber,
                                            batchNumber, config.getTotalBatches()));
                                }

                                context.getBatchCounter(batchNumber).incrementAndGet();

                                return checkBatchThreshold(apiPath, batchNumber, config)
                                        .map(thresholdExceeded -> {
                                            if (thresholdExceeded) {
                                                return new BatchPushResult(false,
                                                        "当前批次流量已达上限，请等待下一批次",
                                                        batchNumber, config.getTotalBatches());
                                            }
                                            return new BatchPushResult(true,
                                                    "推送成功，批次: " + batchNumber,
                                                    batchNumber, config.getTotalBatches());
                                        });
                            });
                });
    }

    private BatchPushContext getOrCreateContext(String apiPath) {
        return pushContexts.computeIfAbsent(apiPath, k -> new BatchPushContext());
    }

    private Mono<Integer> getCurrentBatchNumber(String apiPath) {
        return redisTemplate.opsForValue().get(BATCH_PROGRESS_KEY_PREFIX + apiPath)
                .map(Integer::parseInt)
                .defaultIfEmpty(0);
    }

    private Mono<Boolean> isUserInBatch(String apiPath, String userId, int batchNumber, BatchConfig config) {
        if (userId == null || userId.isEmpty()) {
            return Mono.just(config.isAllowAnonymous());
        }

        int userHash = Math.abs(userId.hashCode());
        int userBatch = (userHash % config.getTotalBatches()) + 1;

        return Mono.just(userBatch <= batchNumber);
    }

    private Mono<Boolean> checkBatchThreshold(String apiPath, int batchNumber, BatchConfig config) {
        String batchCountKey = BATCH_PUSH_KEY_PREFIX + apiPath + ":count:" + batchNumber;
        return redisTemplate.opsForValue().increment(batchCountKey)
                .map(count -> count > config.getBatchSize());
    }

    public Mono<Void> startBatchPush(String apiPath, BatchConfig config) {
        BatchPushContext context = getOrCreateContext(apiPath);
        context.setConfig(config);
        context.setStartTime(System.currentTimeMillis());
        context.resetCounters();

        return redisTemplate.opsForValue().set(BATCH_PROGRESS_KEY_PREFIX + apiPath, "1")
                .then(redisTemplate.expire(BATCH_PROGRESS_KEY_PREFIX + apiPath,
                        Duration.ofMillis(config.getTotalBatches() * config.getBatchIntervalMs() * 2L)))
                .then();
    }

    public Mono<Void> advanceBatch(String apiPath) {
        return redisTemplate.opsForValue().increment(BATCH_PROGRESS_KEY_PREFIX + apiPath)
                .then();
    }

    public Mono<Void> stopBatchPush(String apiPath) {
        BatchPushContext context = pushContexts.remove(apiPath);
        if (context != null) {
            log.info("停止分批推送: {}, 总耗时: {}ms", apiPath,
                    System.currentTimeMillis() - context.getStartTime());
        }
        return redisTemplate.delete(BATCH_PROGRESS_KEY_PREFIX + apiPath)
                .then();
    }

    public Mono<BatchPushStatus> getPushStatus(String apiPath) {
        return getCurrentBatchNumber(apiPath)
                .flatMap(batchNumber -> {
                    BatchPushContext context = pushContexts.get(apiPath);
                    if (context == null) {
                        return Mono.just(new BatchPushStatus(apiPath, false, 0, 0, 0, 0));
                    }

                    BatchConfig config = context.getConfig();
                    long totalProcessed = context.getTotalProcessed();

                    return Mono.just(new BatchPushStatus(
                            apiPath,
                            true,
                            batchNumber,
                            config.getTotalBatches(),
                            totalProcessed,
                            config.getBatchSize()
                    ));
                });
    }

    @Data
    public static class BatchConfig {
        private int totalBatches = 10;
        private int batchSize = 1000;
        private long batchIntervalMs = 3600000;
        private boolean allowAnonymous = false;
    }

    @Data
    public static class BatchPushResult {
        private final boolean allowed;
        private final String message;
        private final int currentBatch;
        private final int totalBatches;

        public BatchPushResult(boolean allowed, String message, int currentBatch, int totalBatches) {
            this.allowed = allowed;
            this.message = message;
            this.currentBatch = currentBatch;
            this.totalBatches = totalBatches;
        }
    }

    @Data
    public static class BatchPushStatus {
        private final String apiPath;
        private final boolean active;
        private final int currentBatch;
        private final int totalBatches;
        private final long totalProcessed;
        private final int batchSize;
    }

    private static class BatchPushContext {
        private BatchConfig config = new BatchConfig();
        private long startTime;
        private final Map<Integer, AtomicInteger> batchCounters = new ConcurrentHashMap<>();

        public AtomicInteger getBatchCounter(int batchNumber) {
            return batchCounters.computeIfAbsent(batchNumber, k -> new AtomicInteger(0));
        }

        public long getTotalProcessed() {
            return batchCounters.values().stream()
                    .mapToLong(AtomicInteger::get)
                    .sum();
        }

        public void resetCounters() {
            batchCounters.clear();
        }
    }
}

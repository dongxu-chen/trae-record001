package com.example.deduplication.quorum;

import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.model.CachedResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuorumService {

    private static final String QUORUM_CACHE_PREFIX = "deduplication:quorum:cache:";
    private static final String QUORUM_LOCK_PREFIX = "deduplication:quorum:lock:";

    private final DeduplicationProperties properties;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private int writeQuorum;
    private long timeoutMs;

    @PostConstruct
    public void init() {
        DeduplicationProperties.QuorumConfig config = properties.getQuorum();
        this.writeQuorum = config.getWriteQuorum();
        this.timeoutMs = config.getOperationTimeoutMs();
        log.info("Quorum service initialized - writeQuorum: {}, timeoutMs: {}", writeQuorum, timeoutMs);
    }

    public Mono<Boolean> quorumSet(String key, CachedResponse response, long ttlSeconds) {
        if (!properties.getQuorum().isEnabled()) {
            return simpleSet(key, response, ttlSeconds);
        }

        String serialized = serialize(response);
        if (serialized == null) {
            return Mono.just(false);
        }

        int totalNodes = properties.getQuorum().getTotalNodes();
        List<Mono<Boolean>> writeOperations = new ArrayList<>();

        for (int i = 0; i < totalNodes; i++) {
            String nodeKey = QUORUM_CACHE_PREFIX + key + ":node" + i;
            int nodeIndex = i;
            writeOperations.add(
                    redisTemplate.opsForValue()
                            .set(nodeKey, serialized, Duration.ofSeconds(ttlSeconds))
                            .doOnNext(success -> log.debug("Node {} write result: {}", nodeIndex, success))
                            .onErrorReturn(false)
            );
        }

        AtomicInteger successCount = new AtomicInteger(0);

        return Flux.merge(writeOperations)
                .take(Duration.ofMillis(timeoutMs))
                .filter(success -> success)
                .take(writeQuorum)
                .doOnNext(success -> successCount.incrementAndGet())
                .collectList()
                .map(results -> {
                    int successful = successCount.get();
                    boolean quorumAchieved = successful >= writeQuorum;
                    log.info("Quorum write completed - successful: {}, required: {}, quorumAchieved: {}",
                            successful, writeQuorum, quorumAchieved);
                    return quorumAchieved;
                })
                .onErrorReturn(false);
    }

    public Mono<CachedResponse> quorumGet(String key) {
        if (!properties.getQuorum().isEnabled()) {
            return simpleGet(key);
        }

        int totalNodes = properties.getQuorum().getTotalNodes();
        List<Mono<CachedResponse>> readOperations = new ArrayList<>();

        for (int i = 0; i < totalNodes; i++) {
            String nodeKey = QUORUM_CACHE_PREFIX + key + ":node" + i;
            readOperations.add(
                    redisTemplate.opsForValue()
                            .get(nodeKey)
                            .map(this::deserialize)
                            .onErrorReturn(null)
            );
        }

        return Flux.merge(readOperations)
                .take(Duration.ofMillis(timeoutMs))
                .filter(response -> response != null)
                .next()
                .switchIfEmpty(Mono.empty());
    }

    public Mono<Boolean> quorumTryLock(String key, long ttlSeconds) {
        if (!properties.getQuorum().isEnabled()) {
            String lockKey = QUORUM_LOCK_PREFIX + key;
            return redisTemplate.opsForValue()
                    .setIfAbsent(lockKey, "locked", Duration.ofSeconds(ttlSeconds));
        }

        int totalNodes = properties.getQuorum().getTotalNodes();
        List<Mono<Boolean>> lockOperations = new ArrayList<>();

        for (int i = 0; i < totalNodes; i++) {
            String nodeKey = QUORUM_LOCK_PREFIX + key + ":node" + i;
            lockOperations.add(
                    redisTemplate.opsForValue()
                            .setIfAbsent(nodeKey, "locked", Duration.ofSeconds(ttlSeconds))
                            .onErrorReturn(false)
            );
        }

        AtomicInteger successCount = new AtomicInteger(0);

        return Flux.merge(lockOperations)
                .take(Duration.ofMillis(timeoutMs))
                .filter(success -> success)
                .take(writeQuorum)
                .doOnNext(success -> successCount.incrementAndGet())
                .collectList()
                .map(results -> successCount.get() >= writeQuorum)
                .onErrorReturn(false);
    }

    public Mono<Long> quorumUnlock(String key) {
        if (!properties.getQuorum().isEnabled()) {
            String lockKey = QUORUM_LOCK_PREFIX + key;
            return redisTemplate.delete(lockKey);
        }

        int totalNodes = properties.getQuorum().getTotalNodes();
        List<Mono<Long>> unlockOperations = new ArrayList<>();

        for (int i = 0; i < totalNodes; i++) {
            String nodeKey = QUORUM_LOCK_PREFIX + key + ":node" + i;
            unlockOperations.add(
                    redisTemplate.delete(nodeKey)
                            .onErrorReturn(0L)
            );
        }

        return Flux.merge(unlockOperations)
                .take(Duration.ofMillis(timeoutMs))
                .collectList()
                .map(results -> results.stream().mapToLong(Long::longValue).sum());
    }

    private Mono<Boolean> simpleSet(String key, CachedResponse response, long ttlSeconds) {
        String cacheKey = QUORUM_CACHE_PREFIX + key;
        String serialized = serialize(response);
        if (serialized == null) {
            return Mono.just(false);
        }
        return redisTemplate.opsForValue()
                .set(cacheKey, serialized, Duration.ofSeconds(ttlSeconds));
    }

    private Mono<CachedResponse> simpleGet(String key) {
        String cacheKey = QUORUM_CACHE_PREFIX + key;
        return redisTemplate.opsForValue()
                .get(cacheKey)
                .map(this::deserialize);
    }

    private String serialize(CachedResponse response) {
        try {
            return objectMapper.writeValueAsString(response);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize response for quorum", e);
            return null;
        }
    }

    private CachedResponse deserialize(String json) {
        try {
            return objectMapper.readValue(json, CachedResponse.class);
        } catch (JsonProcessingException e) {
            log.error("Failed to deserialize response for quorum", e);
            return null;
        }
    }
}

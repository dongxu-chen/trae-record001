package com.example.deduplication.cache;

import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.model.CachedResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class DistributedCacheService {

    private static final String CACHE_PREFIX = "deduplication:cache:";
    private static final String LOCK_PREFIX = "deduplication:lock:";
    private static final long LOCK_EXPIRE_SECONDS = 30;

    private final ReactiveStringRedisTemplate redisTemplate;
    private final DeduplicationProperties properties;
    private final ObjectMapper objectMapper;

    public Mono<CachedResponse> get(String key) {
        String cacheKey = CACHE_PREFIX + key;
        return redisTemplate.opsForValue().get(cacheKey)
                .map(this::deserialize)
                .doOnNext(response -> log.debug("Distributed cache hit for key: {}", key))
                .doOnError(e -> log.error("Error reading from distributed cache", e));
    }

    public Mono<Boolean> set(String key, CachedResponse response) {
        String cacheKey = CACHE_PREFIX + key;
        String value = serialize(response);
        if (value == null) {
            return Mono.just(false);
        }

        return redisTemplate.opsForValue()
                .set(cacheKey, value, Duration.ofSeconds(properties.getCacheExpireSeconds()))
                .doOnNext(success -> log.debug("Distributed cache put for key: {}", key))
                .doOnError(e -> log.error("Error writing to distributed cache", e));
    }

    public Mono<Boolean> tryLock(String key) {
        String lockKey = LOCK_PREFIX + key;
        return redisTemplate.opsForValue()
                .setIfAbsent(lockKey, "locked", Duration.ofSeconds(LOCK_EXPIRE_SECONDS))
                .doOnNext(acquired -> {
                    if (acquired) {
                        log.debug("Lock acquired for key: {}", key);
                    }
                });
    }

    public Mono<Long> unlock(String key) {
        String lockKey = LOCK_PREFIX + key;
        return redisTemplate.delete(lockKey)
                .doOnNext(deleted -> log.debug("Lock released for key: {}", key));
    }

    private String serialize(CachedResponse response) {
        try {
            return objectMapper.writeValueAsString(response);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize response", e);
            return null;
        }
    }

    private CachedResponse deserialize(String json) {
        try {
            return objectMapper.readValue(json, CachedResponse.class);
        } catch (JsonProcessingException e) {
            log.error("Failed to deserialize response", e);
            return null;
        }
    }
}

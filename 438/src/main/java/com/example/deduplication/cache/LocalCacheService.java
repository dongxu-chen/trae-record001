package com.example.deduplication.cache;

import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.model.CachedResponse;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class LocalCacheService {

    private final DeduplicationProperties properties;
    private Cache<String, CachedResponse> caffeineCache;

    @PostConstruct
    public void init() {
        DeduplicationProperties.CaffeineConfig config = properties.getCaffeine();
        caffeineCache = Caffeine.newBuilder()
                .maximumSize(config.getMaximumSize())
                .expireAfterWrite(config.getExpireAfterWriteSeconds(), TimeUnit.SECONDS)
                .recordStats()
                .build();

        log.info("Caffeine cache initialized - maxSize: {}, expireAfterWrite: {}s",
                config.getMaximumSize(), config.getExpireAfterWriteSeconds());
    }

    public CachedResponse get(String key) {
        CachedResponse response = caffeineCache.getIfPresent(key);
        if (response != null) {
            log.debug("Local cache hit for key: {}", key);
        }
        return response;
    }

    public void put(String key, CachedResponse response) {
        caffeineCache.put(key, response);
        log.debug("Local cache put for key: {}", key);
    }

    public void invalidate(String key) {
        caffeineCache.invalidate(key);
        log.debug("Local cache invalidated for key: {}", key);
    }
}

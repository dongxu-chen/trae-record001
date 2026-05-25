package com.apigateway.core.cache;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RMapCacheReactive;
import org.redisson.api.RedissonReactiveClient;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * Redis缓存服务类
 * 使用Redisson响应式客户端实现，提供Mono响应式风格的缓存操作
 * 支持缓存的获取、存储、删除等基本操作
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RedisCacheService {

    /**
     * Redisson响应式客户端
     */
    private final RedissonReactiveClient redissonReactiveClient;

    /**
     * 缓存配置属性
     */
    private final CacheProperties cacheProperties;

    /**
     * 默认缓存名称
     */
    private static final String DEFAULT_CACHE_NAME = "default";

    /**
     * 从缓存中获取数据
     *
     * @param key 缓存Key
     * @param <T> 返回值类型
     * @return 缓存数据，若不存在则返回Mono.empty()
     */
    public <T> Mono<T> get(String key) {
        return get(DEFAULT_CACHE_NAME, key);
    }

    /**
     * 从指定缓存中获取数据
     *
     * @param cacheName 缓存名称
     * @param key       缓存Key
     * @param <T>       返回值类型
     * @return 缓存数据，若不存在则返回Mono.empty()
     */
    @SuppressWarnings("unchecked")
    public <T> Mono<T> get(String cacheName, String key) {
        if (!cacheProperties.isEnabled()) {
            log.debug("缓存未启用，跳过获取 - cacheName: {}, key: {}", cacheName, key);
            return Mono.empty();
        }

        String fullKey = buildFullKey(key);
        log.debug("从缓存获取数据 - cacheName: {}, key: {}, fullKey: {}", cacheName, key, fullKey);

        return getCacheMap(cacheName)
                .get(fullKey)
                .map(value -> {
                    log.debug("缓存命中 - key: {}", fullKey);
                    return (T) value;
                })
                .doOnError(e -> log.error("缓存获取失败 - key: {}, error: {}", fullKey, e.getMessage()))
                .onErrorResume(e -> Mono.empty());
    }

    /**
     * 将数据存入缓存，使用默认过期时间
     *
     * @param key   缓存Key
     * @param value 缓存值
     * @param <T>   值类型
     * @return 操作结果Mono
     */
    public <T> Mono<Void> put(String key, T value) {
        return put(DEFAULT_CACHE_NAME, key, value, cacheProperties.getDefaultExpireTime());
    }

    /**
     * 将数据存入缓存，指定过期时间
     *
     * @param key        缓存Key
     * @param value      缓存值
     * @param expireTime 过期时间
     * @param <T>        值类型
     * @return 操作结果Mono
     */
    public <T> Mono<Void> put(String key, T value, Duration expireTime) {
        return put(DEFAULT_CACHE_NAME, key, value, expireTime);
    }

    /**
     * 将数据存入指定缓存，指定过期时间
     *
     * @param cacheName  缓存名称
     * @param key        缓存Key
     * @param value      缓存值
     * @param expireTime 过期时间
     * @param <T>        值类型
     * @return 操作结果Mono
     */
    public <T> Mono<Void> put(String cacheName, String key, T value, Duration expireTime) {
        if (!cacheProperties.isEnabled()) {
            log.debug("缓存未启用，跳过存储 - cacheName: {}, key: {}", cacheName, key);
            return Mono.empty();
        }

        String fullKey = buildFullKey(key);
        log.debug("存储数据到缓存 - cacheName: {}, key: {}, fullKey: {}, expireTime: {}",
                cacheName, key, fullKey, expireTime);

        return getCacheMap(cacheName)
                .put(fullKey, value, expireTime.toMillis(), TimeUnit.MILLISECONDS)
                .doOnSuccess(v -> log.debug("缓存存储成功 - key: {}", fullKey))
                .doOnError(e -> log.error("缓存存储失败 - key: {}, error: {}", fullKey, e.getMessage()))
                .then();
    }

    /**
     * 如果缓存Key不存在则存储数据
     *
     * @param key   缓存Key
     * @param value 缓存值
     * @param <T>   值类型
     * @return 之前的值，如果不存在则返回null
     */
    public <T> Mono<T> putIfAbsent(String key, T value) {
        return putIfAbsent(DEFAULT_CACHE_NAME, key, value, cacheProperties.getDefaultExpireTime());
    }

    /**
     * 如果缓存Key不存在则存储数据，指定过期时间
     *
     * @param cacheName  缓存名称
     * @param key        缓存Key
     * @param value      缓存值
     * @param expireTime 过期时间
     * @param <T>        值类型
     * @return 之前的值，如果不存在则返回null
     */
    @SuppressWarnings("unchecked")
    public <T> Mono<T> putIfAbsent(String cacheName, String key, T value, Duration expireTime) {
        if (!cacheProperties.isEnabled()) {
            log.debug("缓存未启用，跳过存储 - cacheName: {}, key: {}", cacheName, key);
            return Mono.empty();
        }

        String fullKey = buildFullKey(key);
        log.debug("如果不存在则存储数据到缓存 - cacheName: {}, key: {}, fullKey: {}",
                cacheName, key, fullKey);

        return getCacheMap(cacheName)
                .putIfAbsent(fullKey, value, expireTime.toMillis(), TimeUnit.MILLISECONDS)
                .map(v -> (T) v)
                .doOnError(e -> log.error("缓存存储失败 - key: {}, error: {}", fullKey, e.getMessage()));
    }

    /**
     * 删除缓存项
     *
     * @param key 缓存Key
     * @return 删除结果Mono
     */
    public Mono<Boolean> evict(String key) {
        return evict(DEFAULT_CACHE_NAME, key);
    }

    /**
     * 从指定缓存中删除缓存项
     *
     * @param cacheName 缓存名称
     * @param key       缓存Key
     * @return 删除结果Mono
     */
    public Mono<Boolean> evict(String cacheName, String key) {
        if (!cacheProperties.isEnabled()) {
            log.debug("缓存未启用，跳过删除 - cacheName: {}, key: {}", cacheName, key);
            return Mono.just(false);
        }

        String fullKey = buildFullKey(key);
        log.debug("删除缓存项 - cacheName: {}, key: {}, fullKey: {}", cacheName, key, fullKey);

        return getCacheMap(cacheName)
                .remove(fullKey)
                .map(v -> true)
                .defaultIfEmpty(false)
                .doOnSuccess(result -> log.debug("缓存删除结果 - key: {}, result: {}", fullKey, result))
                .doOnError(e -> log.error("缓存删除失败 - key: {}, error: {}", fullKey, e.getMessage()));
    }

    /**
     * 清空指定缓存
     *
     * @param cacheName 缓存名称
     * @return 操作结果Mono
     */
    public Mono<Void> clear(String cacheName) {
        if (!cacheProperties.isEnabled()) {
            log.debug("缓存未启用，跳过清空 - cacheName: {}", cacheName);
            return Mono.empty();
        }

        log.debug("清空缓存 - cacheName: {}", cacheName);

        return getCacheMap(cacheName)
                .clear()
                .doOnSuccess(v -> log.debug("缓存清空成功 - cacheName: {}", cacheName))
                .doOnError(e -> log.error("缓存清空失败 - cacheName: {}, error: {}", cacheName, e.getMessage()));
    }

    /**
     * 检查缓存Key是否存在
     *
     * @param key 缓存Key
     * @return 是否存在Mono
     */
    public Mono<Boolean> exists(String key) {
        return exists(DEFAULT_CACHE_NAME, key);
    }

    /**
     * 检查指定缓存中Key是否存在
     *
     * @param cacheName 缓存名称
     * @param key       缓存Key
     * @return 是否存在Mono
     */
    public Mono<Boolean> exists(String cacheName, String key) {
        if (!cacheProperties.isEnabled()) {
            return Mono.just(false);
        }

        String fullKey = buildFullKey(key);
        return getCacheMap(cacheName)
                .containsKey(fullKey)
                .doOnError(e -> log.error("检查缓存存在失败 - key: {}, error: {}", fullKey, e.getMessage()))
                .onErrorReturn(false);
    }

    /**
     * 获取缓存剩余过期时间
     *
     * @param key 缓存Key
     * @return 剩余过期时间（毫秒），-1表示永久，-2表示不存在
     */
    public Mono<Long> getRemainingTTL(String key) {
        return getRemainingTTL(DEFAULT_CACHE_NAME, key);
    }

    /**
     * 获取指定缓存中Key的剩余过期时间
     *
     * @param cacheName 缓存名称
     * @param key       缓存Key
     * @return 剩余过期时间（毫秒），-1表示永久，-2表示不存在
     */
    public Mono<Long> getRemainingTTL(String cacheName, String key) {
        if (!cacheProperties.isEnabled()) {
            return Mono.just(-2L);
        }

        String fullKey = buildFullKey(key);
        return getCacheMap(cacheName)
                .remainTimeToLive(fullKey)
                .doOnError(e -> log.error("获取缓存过期时间失败 - key: {}, error: {}", fullKey, e.getMessage()))
                .onErrorReturn(-2L);
    }

    /**
     * 构建完整的缓存Key
     *
     * @param key 原始Key
     * @return 带前缀的完整Key
     */
    private String buildFullKey(String key) {
        return cacheProperties.getKeyPrefix() + ":" + key;
    }

    /**
     * 获取或创建缓存Map
     *
     * @param cacheName 缓存名称
     * @return RMapCacheReactive实例
     */
    private <K, V> RMapCacheReactive<K, V> getCacheMap(String cacheName) {
        return redissonReactiveClient.getMapCache(cacheName);
    }
}

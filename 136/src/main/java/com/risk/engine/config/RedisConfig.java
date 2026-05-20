package com.risk.engine.config;

import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Slf4j
@Configuration
public class RedisConfig {

    private static final int BLOOM_EXPECTED_INSERTIONS = 1000000;
    private static final double BLOOM_FPP = 0.01;

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.afterPropertiesSet();
        return template;
    }

    @Bean
    public BloomFilterManager bloomFilterManager() {
        return new BloomFilterManager();
    }

    public static class BloomFilterManager {
        private final ConcurrentHashMap<String, BloomFilter<String>> filters = new ConcurrentHashMap<>();
        private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

        public BloomFilter<String> getOrCreateFilter(String key) {
            BloomFilter<String> filter = filters.get(key);
            if (filter == null) {
                lock.writeLock().lock();
                try {
                    filter = filters.computeIfAbsent(key, k -> 
                        BloomFilter.create(Funnels.stringFunnel(StandardCharsets.UTF_8), 
                            BLOOM_EXPECTED_INSERTIONS, BLOOM_FPP));
                    log.info("创建布隆过滤器: {}", key);
                } finally {
                    lock.writeLock().unlock();
                }
            }
            return filter;
        }

        public void put(String filterKey, String value) {
            BloomFilter<String> filter = getOrCreateFilter(filterKey);
            lock.readLock().lock();
            try {
                filter.put(value);
            } finally {
                lock.readLock().unlock();
            }
        }

        public boolean mightContain(String filterKey, String value) {
            BloomFilter<String> filter = filters.get(filterKey);
            if (filter == null) {
                return false;
            }
            lock.readLock().lock();
            try {
                return filter.mightContain(value);
            } finally {
                lock.readLock().unlock();
            }
        }

        public void rebuildFilter(String filterKey, Iterable<String> values) {
            lock.writeLock().lock();
            try {
                BloomFilter<String> newFilter = BloomFilter.create(
                    Funnels.stringFunnel(StandardCharsets.UTF_8), 
                    BLOOM_EXPECTED_INSERTIONS, BLOOM_FPP);
                for (String value : values) {
                    newFilter.put(value);
                }
                filters.put(filterKey, newFilter);
                log.info("重建布隆过滤器完成: {}", filterKey);
            } finally {
                lock.writeLock().unlock();
            }
        }

        public void clearFilter(String filterKey) {
            lock.writeLock().lock();
            try {
                filters.remove(filterKey);
                log.info("清除布隆过滤器: {}", filterKey);
            } finally {
                lock.writeLock().unlock();
            }
        }
    }
}

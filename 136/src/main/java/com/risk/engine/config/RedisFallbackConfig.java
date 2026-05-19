package com.risk.engine.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Configuration
public class RedisFallbackConfig {

    @Bean
    @ConditionalOnMissingBean(RedisConnectionFactory.class)
    public RedisTemplate<String, Object> fallbackRedisTemplate() {
        log.warn("Redis连接工厂不存在，使用内存缓存作为降级方案");
        return new InMemoryRedisTemplate();
    }

    public static class InMemoryRedisTemplate extends RedisTemplate<String, Object> {
        
        private final Map<String, Set<Object>> setStore = new ConcurrentHashMap<>();

        public InMemoryRedisTemplate() {
            setKeySerializer(new StringRedisSerializer());
            setValueSerializer(new GenericJackson2JsonRedisSerializer());
            setHashKeySerializer(new StringRedisSerializer());
            setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        }

        @Override
        public Boolean delete(String key) {
            setStore.remove(key);
            return true;
        }

        @Override
        public Boolean expire(String key, long timeout, java.util.concurrent.TimeUnit unit) {
            return true;
        }

        @Override
        public SetOperations<String, Object> opsForSet() {
            return new InMemorySetOperations(setStore);
        }
    }

    public static class InMemorySetOperations implements org.springframework.data.redis.core.SetOperations<String, Object> {
        
        private final Map<String, Set<Object>> setStore;

        public InMemorySetOperations(Map<String, Set<Object>> setStore) {
            this.setStore = setStore;
        }

        @Override
        public Long add(String key, Object... values) {
            Set<Object> set = setStore.computeIfAbsent(key, k -> ConcurrentHashMap.newKeySet());
            long count = 0;
            for (Object value : values) {
                if (set.add(value)) count++;
            }
            return count;
        }

        @Override
        public Long remove(String key, Object... values) {
            Set<Object> set = setStore.get(key);
            if (set == null) return 0L;
            long count = 0;
            for (Object value : values) {
                if (set.remove(value)) count++;
            }
            return count;
        }

        @Override
        public Boolean isMember(String key, Object value) {
            Set<Object> set = setStore.get(key);
            return set != null && set.contains(value);
        }

        @Override
        public Set<Object> members(String key) {
            return setStore.get(key);
        }

        @Override
        public Long size(String key) {
            Set<Object> set = setStore.get(key);
            return set != null ? (long) set.size() : 0L;
        }

        @Override
        public Object randomMember(String key) { return null; }
        @Override
        public Set<Object> distinctRandomMembers(String key, long count) { return null; }
        @Override
        public List<Object> randomMembers(String key, long count) { return null; }
        @Override
        public Boolean move(String key, Object value, String destKey) { return false; }
        @Override
        public Object pop(String key) { return null; }
        @Override
        public List<Object> pop(String key, long count) { return null; }
        @Override
        public Set<Object> intersect(Collection<String> keys) { return null; }
        @Override
        public Set<Object> intersect(String key, String otherKey) { return null; }
        @Override
        public Long intersectAndStore(Collection<String> keys, String destKey) { return null; }
        @Override
        public Long intersectAndStore(String key, String otherKey, String destKey) { return null; }
        @Override
        public Set<Object> union(Collection<String> keys) { return null; }
        @Override
        public Set<Object> union(String key, String otherKey) { return null; }
        @Override
        public Long unionAndStore(Collection<String> keys, String destKey) { return null; }
        @Override
        public Long unionAndStore(String key, String otherKey, String destKey) { return null; }
        @Override
        public Set<Object> difference(Collection<String> keys) { return null; }
        @Override
        public Set<Object> difference(String key, String otherKey) { return null; }
        @Override
        public Long differenceAndStore(Collection<String> keys, String destKey) { return null; }
        @Override
        public Long differenceAndStore(String key, String otherKey, String destKey) { return null; }
        @Override
        public Cursor<Object> scan(String key, org.springframework.data.redis.core.ScanOptions options) { return null; }
        @Override
        public RedisOperations<String, Object> getOperations() { return null; }
    }
}

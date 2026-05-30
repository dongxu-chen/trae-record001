package com.replay.detector.service;

import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import com.replay.detector.config.ReplayDetectionProperties;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class BloomFilterService {

    private static final String BLOOM_SET_KEY = "replay:bloom:set";
    private static final String CONFIRM_HASH_KEY = "replay:bloom:confirm";

    private final StringRedisTemplate redisTemplate;
    private final ReplayDetectionProperties properties;

    private BloomFilter<String> localBloomFilter;

    private static final String BLOOM_ADD_SCRIPT =
            "local setKey = KEYS[1] " +
            "local hashKey = KEYS[2] " +
            "local member = ARGV[1] " +
            "local ttl = tonumber(ARGV[2]) " +
            "local exists = redis.call('SISMEMBER', setKey, member) " +
            "if exists == 1 then return 1 end " +
            "redis.call('SADD', setKey, member) " +
            "redis.call('EXPIRE', setKey, ttl) " +
            "redis.call('HSET', hashKey, member, '1') " +
            "redis.call('EXPIRE', hashKey, ttl) " +
            "return 0 ";

    private static final String BLOOM_CHECK_SCRIPT =
            "local setKey = KEYS[1] " +
            "local member = ARGV[1] " +
            "return redis.call('SISMEMBER', setKey, member) ";

    private static final String CONFIRM_SCRIPT =
            "local hashKey = KEYS[1] " +
            "local member = ARGV[1] " +
            "return redis.call('HEXISTS', hashKey, member) ";

    public BloomFilterService(StringRedisTemplate redisTemplate, ReplayDetectionProperties properties) {
        this.redisTemplate = redisTemplate;
        this.properties = properties;
    }

    @PostConstruct
    public void init() {
        ReplayDetectionProperties.BloomFilter bf = properties.getBloomFilter();
        localBloomFilter = BloomFilter.create(
                Funnels.stringFunnel(StandardCharsets.UTF_8),
                bf.getExpectedInsertions(),
                bf.getFalseProbability()
        );
        log.info("Local bloom filter initialized: expectedInsertions={}, falseProbability={}, confirmationEnabled={}",
                bf.getExpectedInsertions(), bf.getFalseProbability(), bf.isConfirmationEnabled());
    }

    public boolean mightContainLocal(String fingerprintHash) {
        return localBloomFilter.mightContain(fingerprintHash);
    }

    public void putLocal(String fingerprintHash) {
        localBloomFilter.put(fingerprintHash);
    }

    public boolean checkAndMarkDistributed(String fingerprintHash) {
        long ttl = properties.getWindowSizeSeconds() * 2L;

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(BLOOM_ADD_SCRIPT, Long.class);
        Long result = redisTemplate.execute(
                script,
                java.util.List.of(BLOOM_SET_KEY, CONFIRM_HASH_KEY),
                fingerprintHash,
                String.valueOf(ttl)
        );

        return result != null && result == 1L;
    }

    public boolean checkDistributed(String fingerprintHash) {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>(BLOOM_CHECK_SCRIPT, Long.class);
        Long result = redisTemplate.execute(
                script,
                Collections.singletonList(BLOOM_SET_KEY),
                fingerprintHash
        );

        return result != null && result == 1L;
    }

    public boolean confirmHit(String fingerprintHash) {
        if (!properties.getBloomFilter().isConfirmationEnabled()) {
            return true;
        }

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(CONFIRM_SCRIPT, Long.class);
        Long result = redisTemplate.execute(
                script,
                Collections.singletonList(CONFIRM_HASH_KEY),
                fingerprintHash
        );

        boolean confirmed = result != null && result == 1L;
        if (!confirmed) {
            log.info("Bloom filter false positive eliminated for hash: {}", fingerprintHash);
        }
        return confirmed;
    }

    public void resetLocal() {
        ReplayDetectionProperties.BloomFilter bf = properties.getBloomFilter();
        localBloomFilter = BloomFilter.create(
                Funnels.stringFunnel(StandardCharsets.UTF_8),
                bf.getExpectedInsertions(),
                bf.getFalseProbability()
        );
        log.info("Local bloom filter has been reset");
    }

    public void cleanupDistributedExpired() {
        Long setTtl = redisTemplate.getExpire(BLOOM_SET_KEY, TimeUnit.SECONDS);
        if (setTtl != null && setTtl <= 0) {
            redisTemplate.delete(BLOOM_SET_KEY);
            redisTemplate.delete(CONFIRM_HASH_KEY);
            log.info("Cleaned up expired distributed bloom filter set and confirmation hash");
        }
    }
}

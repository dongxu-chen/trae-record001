package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class DistributedLockService {

    private final StringRedisTemplate redisTemplate;
    private final ReplayDetectionProperties properties;

    public String tryLock(String fingerprintHash) {
        String lockKey = properties.getDistributed().getKeyPrefix() + fingerprintHash;
        String lockValue = UUID.randomUUID().toString();
        int timeout = properties.getDistributed().getLockTimeoutSeconds();

        Boolean acquired = redisTemplate.opsForValue()
                .setIfAbsent(lockKey, lockValue, timeout, TimeUnit.SECONDS);

        if (Boolean.TRUE.equals(acquired)) {
            log.debug("Acquired distributed lock: key={}, value={}", lockKey, lockValue);
            return lockValue;
        }

        log.debug("Failed to acquire distributed lock: key={}", lockKey);
        return null;
    }

    public boolean releaseLock(String fingerprintHash, String lockValue) {
        String lockKey = properties.getDistributed().getKeyPrefix() + fingerprintHash;

        String currentValue = redisTemplate.opsForValue().get(lockKey);
        if (lockValue.equals(currentValue)) {
            Boolean deleted = redisTemplate.delete(lockKey);
            log.debug("Released distributed lock: key={}, success={}", lockKey, deleted);
            return Boolean.TRUE.equals(deleted);
        }

        log.warn("Lock value mismatch, cannot release: key={}, expected={}, actual={}",
                lockKey, lockValue, currentValue);
        return false;
    }
}

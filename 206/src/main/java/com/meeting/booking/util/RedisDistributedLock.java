package com.meeting.booking.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class RedisDistributedLock {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String LOCK_PREFIX = "booking:lock:";
    private static final long DEFAULT_WAIT_TIME = 0;
    private static final long DEFAULT_LEASE_TIME = 3;

    private static final String UNLOCK_SCRIPT =
            "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                    "return redis.call('del', KEYS[1]) " +
                    "else " +
                    "return 0 " +
                    "end";

    public String tryLock(String lockKey) {
        return tryLock(lockKey, DEFAULT_WAIT_TIME, DEFAULT_LEASE_TIME, TimeUnit.SECONDS);
    }

    public String tryLock(String lockKey, long waitTime, long leaseTime, TimeUnit timeUnit) {
        String key = LOCK_PREFIX + lockKey;
        String requestId = UUID.randomUUID().toString();
        long timeout = System.currentTimeMillis() + timeUnit.toMillis(waitTime);

        try {
            while (System.currentTimeMillis() < timeout || waitTime == 0) {
                Boolean success = redisTemplate.opsForValue()
                        .setIfAbsent(key, requestId, leaseTime, timeUnit);

                if (Boolean.TRUE.equals(success)) {
                    log.debug("Acquired lock: {}, requestId: {}", key, requestId);
                    return requestId;
                }

                if (waitTime == 0) {
                    break;
                }

                Thread.sleep(50);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Lock acquisition interrupted: {}", key);
        }

        log.debug("Failed to acquire lock: {}", key);
        return null;
    }

    public boolean unlock(String lockKey, String requestId) {
        if (requestId == null) {
            return false;
        }

        String key = LOCK_PREFIX + lockKey;
        DefaultRedisScript<Long> script = new DefaultRedisScript<>(UNLOCK_SCRIPT, Long.class);

        Long result = redisTemplate.execute(script, Collections.singletonList(key), requestId);

        if (Long.valueOf(1).equals(result)) {
            log.debug("Released lock: {}, requestId: {}", key, requestId);
            return true;
        } else {
            log.debug("Lock already released or not owned: {}, requestId: {}", key, requestId);
            return false;
        }
    }

    public boolean isLocked(String lockKey) {
        String key = LOCK_PREFIX + lockKey;
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }
}

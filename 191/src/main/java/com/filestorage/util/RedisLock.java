package com.filestorage.util;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import jakarta.annotation.Resource;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

@Component
public class RedisLock {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    private static final String LOCK_PREFIX = "lock:";
    private static final long DEFAULT_WAIT_TIME = 3000;
    private static final long DEFAULT_LEASE_TIME = 10000;

    private static final DefaultRedisScript<Long> UNLOCK_SCRIPT = new DefaultRedisScript<>(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
            Long.class
    );

    public boolean tryLock(String key, String value) {
        return tryLock(key, value, DEFAULT_WAIT_TIME, DEFAULT_LEASE_TIME, TimeUnit.MILLISECONDS);
    }

    public boolean tryLock(String key, String value, long waitTime, long leaseTime, TimeUnit unit) {
        String lockKey = LOCK_PREFIX + key;
        long startTime = System.currentTimeMillis();
        long waitMillis = unit.toMillis(waitTime);

        while (true) {
            Boolean result = redisTemplate.opsForValue().setIfAbsent(lockKey, value, leaseTime, unit);
            if (Boolean.TRUE.equals(result)) {
                return true;
            }

            if (System.currentTimeMillis() - startTime > waitMillis) {
                return false;
            }

            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
    }

    public boolean unlock(String key, String value) {
        String lockKey = LOCK_PREFIX + key;
        Long result = redisTemplate.execute(UNLOCK_SCRIPT, Collections.singletonList(lockKey), value);
        return Long.valueOf(1).equals(result);
    }
}

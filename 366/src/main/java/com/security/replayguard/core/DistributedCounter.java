package com.security.replayguard.core;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class DistributedCounter {

    private static final String KEY_PREFIX = "replay:counter:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> distributedCounterScript;

    public long increment(String key, long maxCount, int windowSeconds) {
        String redisKey = KEY_PREFIX + key;

        try {
            List<String> keys = Collections.singletonList(redisKey);
            Long result = redisTemplate.execute(
                    distributedCounterScript,
                    keys,
                    "1",
                    String.valueOf(maxCount),
                    String.valueOf(windowSeconds)
            );

            return result != null ? result : 0;
        } catch (Exception e) {
            log.error("Distributed counter error for key: {}", key, e);
            return maxCount + 1;
        }
    }

    public long increment(String key, long increment, long maxCount, int windowSeconds) {
        String redisKey = KEY_PREFIX + key;

        try {
            List<String> keys = Collections.singletonList(redisKey);
            Long result = redisTemplate.execute(
                    distributedCounterScript,
                    keys,
                    String.valueOf(increment),
                    String.valueOf(maxCount),
                    String.valueOf(windowSeconds)
            );

            return result != null ? result : 0;
        } catch (Exception e) {
            log.error("Distributed counter error for key: {}", key, e);
            return maxCount + 1;
        }
    }

    public long getCount(String key) {
        String redisKey = KEY_PREFIX + key;

        try {
            String value = redisTemplate.opsForValue().get(redisKey);
            return value != null ? Long.parseLong(value) : 0;
        } catch (Exception e) {
            log.error("Get count error for key: {}", key, e);
            return 0;
        }
    }

    public void reset(String key) {
        String redisKey = KEY_PREFIX + key;

        try {
            redisTemplate.delete(redisKey);
        } catch (Exception e) {
            log.error("Reset counter error for key: {}", key, e);
        }
    }

    public boolean isThresholdExceeded(String key, long threshold) {
        long count = getCount(key);
        return count >= threshold;
    }
}

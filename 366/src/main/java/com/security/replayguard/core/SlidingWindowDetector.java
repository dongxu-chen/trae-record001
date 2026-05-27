package com.security.replayguard.core;

import com.security.replayguard.config.ReplayGuardProperties;
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
public class SlidingWindowDetector {

    private static final String KEY_PREFIX = "replay:sliding:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> slidingWindowScript;
    private final ReplayGuardProperties properties;

    public boolean isAllowed(String uniqueHash) {
        String key = KEY_PREFIX + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        int windowSeconds = properties.getSlidingWindow().getTimeWindowSeconds();
        int maxRequests = properties.getSlidingWindow().getMaxRequestsPerWindow();
        String requestId = uniqueHash + ":" + now + ":" + System.nanoTime();

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    slidingWindowScript,
                    keys,
                    String.valueOf(now),
                    String.valueOf(windowSeconds),
                    String.valueOf(maxRequests),
                    requestId
            );

            if (result != null && result == 1) {
                log.debug("Sliding window check passed for key: {}", uniqueHash);
                return true;
            } else {
                log.warn("Sliding window check blocked for key: {}, request limit exceeded", uniqueHash);
                return false;
            }
        } catch (Exception e) {
            log.error("Sliding window check error for key: {}", uniqueHash, e);
            return true;
        }
    }

    public long getCurrentWindowCount(String uniqueHash) {
        String key = KEY_PREFIX + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        long windowStart = now - properties.getSlidingWindow().getTimeWindowSeconds();

        try {
            redisTemplate.opsForZSet().removeRangeByScore(key, Double.NEGATIVE_INFINITY, windowStart);
            Long count = redisTemplate.opsForZSet().zCard(key);
            return count != null ? count : 0;
        } catch (Exception e) {
            log.error("Get window count error for key: {}", uniqueHash, e);
            return 0;
        }
    }

    public void cleanExpired(String uniqueHash) {
        String key = KEY_PREFIX + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        long windowStart = now - properties.getSlidingWindow().getTimeWindowSeconds();

        try {
            redisTemplate.opsForZSet().removeRangeByScore(key, Double.NEGATIVE_INFINITY, windowStart);
        } catch (Exception e) {
            log.error("Clean expired error for key: {}", uniqueHash, e);
        }
    }
}

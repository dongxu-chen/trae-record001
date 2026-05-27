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
public class DualBufferSlidingWindowDetector {

    private static final String KEY_PREFIX_CURRENT = "replay:dual:current:";
    private static final String KEY_PREFIX_PREVIOUS = "replay:dual:previous:";
    private static final String KEY_PREFIX_META = "replay:dual:meta:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> dualBufferSlidingWindowScript;
    private final ReplayGuardProperties properties;

    public boolean isAllowed(String uniqueHash, String partitionKey) {
        if (!properties.getSlidingWindow().isDualBufferEnabled()) {
            return isAllowedSingleBuffer(uniqueHash, partitionKey);
        }

        return isAllowedDualBuffer(uniqueHash, partitionKey);
    }

    private boolean isAllowedSingleBuffer(String uniqueHash, String partitionKey) {
        String key = KEY_PREFIX_CURRENT + partitionKey + ":" + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        int windowSeconds = properties.getSlidingWindow().getTimeWindowSeconds();
        int maxRequests = properties.getSlidingWindow().getMaxRequestsPerWindow();
        String requestId = uniqueHash + ":" + now + ":" + System.nanoTime();

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    dualBufferSlidingWindowScript,
                    keys,
                    String.valueOf(now),
                    String.valueOf(windowSeconds),
                    String.valueOf(maxRequests),
                    requestId,
                    "0",
                    "0",
                    "0"
            );

            if (result != null && result == 1) {
                log.debug("Single buffer window check passed for key: {}", uniqueHash);
                return true;
            } else {
                log.warn("Single buffer window check blocked for key: {}", uniqueHash);
                return false;
            }
        } catch (Exception e) {
            log.error("Single buffer window check error for key: {}", uniqueHash, e);
            return true;
        }
    }

    private boolean isAllowedDualBuffer(String uniqueHash, String partitionKey) {
        String currentKey = KEY_PREFIX_CURRENT + partitionKey + ":" + uniqueHash;
        String previousKey = KEY_PREFIX_PREVIOUS + partitionKey + ":" + uniqueHash;
        String metaKey = KEY_PREFIX_META + partitionKey + ":" + uniqueHash;

        long now = System.currentTimeMillis() / 1000;
        int windowSeconds = properties.getSlidingWindow().getTimeWindowSeconds();
        int overlapSeconds = properties.getSlidingWindow().getOverlapSeconds();
        int maxRequests = properties.getSlidingWindow().getMaxRequestsPerWindow();
        String requestId = uniqueHash + ":" + now + ":" + System.nanoTime();

        try {
            List<String> keys = List.of(currentKey, previousKey, metaKey);
            Long result = redisTemplate.execute(
                    dualBufferSlidingWindowScript,
                    keys,
                    String.valueOf(now),
                    String.valueOf(windowSeconds),
                    String.valueOf(maxRequests),
                    requestId,
                    String.valueOf(overlapSeconds),
                    "1",
                    "1"
            );

            if (result != null && result == 1) {
                log.debug("Dual buffer window check passed for key: {}, partition: {}", uniqueHash, partitionKey);
                return true;
            } else {
                log.warn("Dual buffer window check blocked for key: {}, partition: {}, result: {}", 
                        uniqueHash, partitionKey, result);
                return false;
            }
        } catch (Exception e) {
            log.error("Dual buffer window check error for key: {}, partition: {}", uniqueHash, partitionKey, e);
            return true;
        }
    }

    public long getCurrentWindowCount(String uniqueHash, String partitionKey) {
        String currentKey = KEY_PREFIX_CURRENT + partitionKey + ":" + uniqueHash;
        String previousKey = KEY_PREFIX_PREVIOUS + partitionKey + ":" + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        long windowStart = now - properties.getSlidingWindow().getTimeWindowSeconds();
        int overlapSeconds = properties.getSlidingWindow().getOverlapSeconds();
        long overlapStart = now - overlapSeconds;

        try {
            redisTemplate.opsForZSet().removeRangeByScore(currentKey, Double.NEGATIVE_INFINITY, windowStart);
            redisTemplate.opsForZSet().removeRangeByScore(previousKey, Double.NEGATIVE_INFINITY, windowStart);

            Long currentCount = redisTemplate.opsForZSet().zCard(currentKey);
            Long previousOverlapCount = redisTemplate.opsForZSet().count(previousKey, overlapStart, now);

            long total = (currentCount != null ? currentCount : 0) + 
                        (previousOverlapCount != null ? previousOverlapCount : 0);
            
            return total;
        } catch (Exception e) {
            log.error("Get window count error for key: {}", uniqueHash, e);
            return 0;
        }
    }

    public WindowStatus getWindowStatus(String uniqueHash, String partitionKey) {
        String metaKey = KEY_PREFIX_META + partitionKey + ":" + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        int windowSeconds = properties.getSlidingWindow().getTimeWindowSeconds();
        int overlapSeconds = properties.getSlidingWindow().getOverlapSeconds();

        try {
            String lastSwitchStr = redisTemplate.opsForValue().get(metaKey);
            long lastSwitch = lastSwitchStr != null ? Long.parseLong(lastSwitchStr) : now;
            
            boolean inOverlap = (now - lastSwitch) <= overlapSeconds;
            boolean needsSwitch = (now - lastSwitch) >= windowSeconds;

            WindowStatus status = new WindowStatus();
            status.setInOverlapPeriod(inOverlap);
            status.setNeedsWindowSwitch(needsSwitch);
            status.setLastSwitchTime(lastSwitch);
            status.setCurrentWindowCount(getCurrentWindowCount(uniqueHash, partitionKey));
            
            return status;
        } catch (Exception e) {
            log.error("Get window status error for key: {}", uniqueHash, e);
            return new WindowStatus();
        }
    }

    public void forceSwitchWindow(String uniqueHash, String partitionKey) {
        String currentKey = KEY_PREFIX_CURRENT + partitionKey + ":" + uniqueHash;
        String previousKey = KEY_PREFIX_PREVIOUS + partitionKey + ":" + uniqueHash;
        String metaKey = KEY_PREFIX_META + partitionKey + ":" + uniqueHash;

        try {
            redisTemplate.rename(currentKey, previousKey);
            
            long now = System.currentTimeMillis() / 1000;
            redisTemplate.opsForValue().set(metaKey, String.valueOf(now));
            
            log.info("Forced window switch for key: {}, partition: {}", uniqueHash, partitionKey);
        } catch (Exception e) {
            log.error("Force window switch error for key: {}", uniqueHash, e);
        }
    }

    public void cleanExpired(String uniqueHash, String partitionKey) {
        String currentKey = KEY_PREFIX_CURRENT + partitionKey + ":" + uniqueHash;
        String previousKey = KEY_PREFIX_PREVIOUS + partitionKey + ":" + uniqueHash;
        long now = System.currentTimeMillis() / 1000;
        long windowStart = now - properties.getSlidingWindow().getTimeWindowSeconds();

        try {
            redisTemplate.opsForZSet().removeRangeByScore(currentKey, Double.NEGATIVE_INFINITY, windowStart);
            redisTemplate.opsForZSet().removeRangeByScore(previousKey, Double.NEGATIVE_INFINITY, windowStart);
        } catch (Exception e) {
            log.error("Clean expired error for key: {}", uniqueHash, e);
        }
    }

    public static class WindowStatus {
        private boolean inOverlapPeriod;
        private boolean needsWindowSwitch;
        private long lastSwitchTime;
        private long currentWindowCount;

        public boolean isInOverlapPeriod() {
            return inOverlapPeriod;
        }

        public void setInOverlapPeriod(boolean inOverlapPeriod) {
            this.inOverlapPeriod = inOverlapPeriod;
        }

        public boolean isNeedsWindowSwitch() {
            return needsWindowSwitch;
        }

        public void setNeedsWindowSwitch(boolean needsWindowSwitch) {
            this.needsWindowSwitch = needsWindowSwitch;
        }

        public long getLastSwitchTime() {
            return lastSwitchTime;
        }

        public void setLastSwitchTime(long lastSwitchTime) {
            this.lastSwitchTime = lastSwitchTime;
        }

        public long getCurrentWindowCount() {
            return currentWindowCount;
        }

        public void setCurrentWindowCount(long currentWindowCount) {
            this.currentWindowCount = currentWindowCount;
        }
    }
}

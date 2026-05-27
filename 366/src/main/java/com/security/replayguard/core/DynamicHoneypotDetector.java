package com.security.replayguard.core;

import com.security.replayguard.config.ReplayGuardProperties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.List;
import java.util.Set;

@Slf4j
@Component
@RequiredArgsConstructor
public class DynamicHoneypotDetector {

    private static final String KEY_PREFIX = "replay:honeypot:";
    private static final String HISTORY_KEY_PREFIX = "replay:honeypot:history:";
    private static final String THRESHOLD_KEY_PREFIX = "replay:honeypot:threshold:";
    private static final String ADJUSTMENT_KEY_PREFIX = "replay:honeypot:adjust:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> dynamicHoneypotScript;
    private final ReplayGuardProperties properties;

    private volatile long currentGlobalThreshold;
    private volatile long lastAdjustmentTime;

    @PostConstruct
    public void init() {
        currentGlobalThreshold = properties.getHoneypot().getSlowThresholdMs();
        lastAdjustmentTime = System.currentTimeMillis() / 1000;
        log.info("Dynamic honeypot detector initialized with threshold: {}ms", currentGlobalThreshold);
    }

    @Scheduled(fixedDelayString = "${replay-guard.honeypot.adjustment-interval-seconds:300}", timeUnit = java.util.concurrent.TimeUnit.SECONDS)
    public void adjustThresholds() {
        if (!properties.getHoneypot().isDynamicThresholdEnabled()) {
            return;
        }

        try {
            long now = System.currentTimeMillis() / 1000;
            int windowSeconds = properties.getHoneypot().getHistoryWindowMinutes() * 60;
            
            String globalHistoryKey = HISTORY_KEY_PREFIX + "global";
            Set<String> historyMembers = redisTemplate.opsForZSet().rangeByScore(
                    globalHistoryKey, 
                    now - windowSeconds, 
                    now
            );

            if (historyMembers != null && historyMembers.size() >= 10) {
                List<Long> responseTimes = historyMembers.stream()
                        .map(s -> {
                            try {
                                return Long.parseLong(s.split(":")[0]);
                            } catch (Exception e) {
                                return null;
                            }
                        })
                        .filter(java.util.Objects::nonNull)
                        .sorted()
                        .toList();

                if (!responseTimes.isEmpty()) {
                    double percentile = properties.getHoneypot().getPercentile();
                    int index = (int) Math.ceil(percentile * responseTimes.size()) - 1;
                    index = Math.max(0, Math.min(index, responseTimes.size() - 1));
                    
                    long newThreshold = responseTimes.get(index) * 2;
                    newThreshold = Math.max(properties.getHoneypot().getMinThresholdMs(), 
                            Math.min(newThreshold, properties.getHoneypot().getMaxThresholdMs()));

                    long oldThreshold = currentGlobalThreshold;
                    currentGlobalThreshold = newThreshold;
                    lastAdjustmentTime = now;

                    redisTemplate.opsForValue().set(
                            THRESHOLD_KEY_PREFIX + "global",
                            String.valueOf(newThreshold)
                    );

                    log.info("Global threshold adjusted from {}ms to {}ms based on {} historical samples (percentile: {})",
                            oldThreshold, newThreshold, responseTimes.size(), percentile);
                }
            }

            cleanExpiredHistory(now, windowSeconds);
        } catch (Exception e) {
            log.error("Error adjusting thresholds", e);
        }
    }

    public HoneypotResult check(String clientIdentifier, long requestTimeMs) {
        if (!properties.getHoneypot().isEnabled()) {
            return new HoneypotResult(false, false);
        }

        recordHistory(clientIdentifier, requestTimeMs);

        long dynamicThreshold = getDynamicThreshold(clientIdentifier);
        int maxSlow = properties.getHoneypot().getMaxSlowRequests();
        int blockDuration = properties.getHoneypot().getBlockDurationSeconds();

        String key = KEY_PREFIX + clientIdentifier;

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    dynamicHoneypotScript,
                    keys,
                    String.valueOf(dynamicThreshold),
                    String.valueOf(maxSlow),
                    String.valueOf(blockDuration),
                    String.valueOf(requestTimeMs)
            );

            if (result != null) {
                switch (result.intValue()) {
                    case 2:
                        log.warn("Honeypot triggered, client blocked: {}, threshold: {}ms, actual: {}ms",
                                clientIdentifier, dynamicThreshold, requestTimeMs);
                        return new HoneypotResult(true, true);
                    case 1:
                        if (requestTimeMs > dynamicThreshold) {
                            log.info("Honeypot recorded slow request from: {}, time: {}ms, threshold: {}ms",
                                    clientIdentifier, requestTimeMs, dynamicThreshold);
                            return new HoneypotResult(true, false);
                        }
                        return new HoneypotResult(false, false);
                    default:
                        return new HoneypotResult(false, false);
                }
            }

            return new HoneypotResult(false, false);
        } catch (Exception e) {
            log.error("Honeypot check error for: {}", clientIdentifier, e);
            return new HoneypotResult(false, false);
        }
    }

    private long getDynamicThreshold(String clientIdentifier) {
        if (!properties.getHoneypot().isDynamicThresholdEnabled()) {
            return properties.getHoneypot().getSlowThresholdMs();
        }

        try {
            String thresholdStr = redisTemplate.opsForValue().get(THRESHOLD_KEY_PREFIX + clientIdentifier);
            if (thresholdStr != null) {
                return Long.parseLong(thresholdStr);
            }
        } catch (Exception e) {
            log.debug("Error getting client-specific threshold for: {}", clientIdentifier, e);
        }

        return currentGlobalThreshold;
    }

    private void recordHistory(String clientIdentifier, long requestTimeMs) {
        if (!properties.getHoneypot().isDynamicThresholdEnabled()) {
            return;
        }

        try {
            long now = System.currentTimeMillis() / 1000;
            String historyEntry = requestTimeMs + ":" + now;

            String globalHistoryKey = HISTORY_KEY_PREFIX + "global";
            redisTemplate.opsForZSet().add(globalHistoryKey, historyEntry, now);
            redisTemplate.expire(globalHistoryKey, 
                    java.time.Duration.ofMinutes(properties.getHoneypot().getHistoryWindowMinutes()));

            String clientHistoryKey = HISTORY_KEY_PREFIX + clientIdentifier;
            redisTemplate.opsForZSet().add(clientHistoryKey, historyEntry, now);
            redisTemplate.expire(clientHistoryKey, 
                    java.time.Duration.ofMinutes(properties.getHoneypot().getHistoryWindowMinutes()));
        } catch (Exception e) {
            log.debug("Error recording history for: {}", clientIdentifier, e);
        }
    }

    private void cleanExpiredHistory(long now, int windowSeconds) {
        try {
            String globalHistoryKey = HISTORY_KEY_PREFIX + "global";
            redisTemplate.opsForZSet().removeRangeByScore(
                    globalHistoryKey, 
                    Double.NEGATIVE_INFINITY, 
                    now - windowSeconds
            );
        } catch (Exception e) {
            log.debug("Error cleaning expired history", e);
        }
    }

    public boolean isBlocked(String clientIdentifier) {
        String blockKey = KEY_PREFIX + clientIdentifier + ":blocked";

        try {
            return Boolean.TRUE.equals(redisTemplate.hasKey(blockKey));
        } catch (Exception e) {
            log.error("Check blocked status error for: {}", clientIdentifier, e);
            return false;
        }
    }

    public void unblock(String clientIdentifier) {
        String blockKey = KEY_PREFIX + clientIdentifier + ":blocked";
        String counterKey = KEY_PREFIX + clientIdentifier;

        try {
            redisTemplate.delete(blockKey);
            redisTemplate.delete(counterKey);
            
            String thresholdKey = THRESHOLD_KEY_PREFIX + clientIdentifier;
            redisTemplate.delete(thresholdKey);
            
            log.info("Honeypot unblocked client: {}", clientIdentifier);
        } catch (Exception e) {
            log.error("Unblock error for: {}", clientIdentifier, e);
        }
    }

    public long getSlowRequestCount(String clientIdentifier) {
        String key = KEY_PREFIX + clientIdentifier;

        try {
            String value = redisTemplate.opsForValue().get(key);
            return value != null ? Long.parseLong(value) : 0;
        } catch (Exception e) {
            log.error("Get slow request count error for: {}", clientIdentifier, e);
            return 0;
        }
    }

    public long getCurrentThreshold(String clientIdentifier) {
        return getDynamicThreshold(clientIdentifier);
    }

    public long getGlobalThreshold() {
        return currentGlobalThreshold;
    }

    public ThresholdStats getThresholdStats(String clientIdentifier) {
        ThresholdStats stats = new ThresholdStats();
        stats.setGlobalThreshold(currentGlobalThreshold);
        stats.setClientThreshold(getDynamicThreshold(clientIdentifier));
        stats.setLastAdjustmentTime(lastAdjustmentTime);
        stats.setDynamicEnabled(properties.getHoneypot().isDynamicThresholdEnabled());
        
        try {
            String historyKey = HISTORY_KEY_PREFIX + clientIdentifier;
            Long historySize = redisTemplate.opsForZSet().zCard(historyKey);
            stats.setHistorySampleCount(historySize != null ? historySize : 0);
        } catch (Exception e) {
            stats.setHistorySampleCount(0);
        }

        return stats;
    }

    public static class HoneypotResult {
        private final boolean isSlowRequest;
        private final boolean isBlocked;

        public HoneypotResult(boolean isSlowRequest, boolean isBlocked) {
            this.isSlowRequest = isSlowRequest;
            this.isBlocked = isBlocked;
        }

        public boolean isSlowRequest() {
            return isSlowRequest;
        }

        public boolean isBlocked() {
            return isBlocked;
        }
    }

    public static class ThresholdStats {
        private long globalThreshold;
        private long clientThreshold;
        private long lastAdjustmentTime;
        private boolean dynamicEnabled;
        private long historySampleCount;

        public long getGlobalThreshold() {
            return globalThreshold;
        }

        public void setGlobalThreshold(long globalThreshold) {
            this.globalThreshold = globalThreshold;
        }

        public long getClientThreshold() {
            return clientThreshold;
        }

        public void setClientThreshold(long clientThreshold) {
            this.clientThreshold = clientThreshold;
        }

        public long getLastAdjustmentTime() {
            return lastAdjustmentTime;
        }

        public void setLastAdjustmentTime(long lastAdjustmentTime) {
            this.lastAdjustmentTime = lastAdjustmentTime;
        }

        public boolean isDynamicEnabled() {
            return dynamicEnabled;
        }

        public void setDynamicEnabled(boolean dynamicEnabled) {
            this.dynamicEnabled = dynamicEnabled;
        }

        public long getHistorySampleCount() {
            return historySampleCount;
        }

        public void setHistorySampleCount(long historySampleCount) {
            this.historySampleCount = historySampleCount;
        }
    }
}

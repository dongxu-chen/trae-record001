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
public class HoneypotDetector {

    private static final String KEY_PREFIX = "replay:honeypot:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> honeypotScript;
    private final ReplayGuardProperties properties;

    public HoneypotResult check(String clientIdentifier, long requestTimeMs) {
        if (!properties.getHoneypot().isEnabled()) {
            return new HoneypotResult(false, false);
        }

        String key = KEY_PREFIX + clientIdentifier;
        int slowThreshold = properties.getHoneypot().getSlowThresholdMs();
        int maxSlow = properties.getHoneypot().getMaxSlowRequests();
        int blockDuration = properties.getHoneypot().getBlockDurationSeconds();

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    honeypotScript,
                    keys,
                    String.valueOf(slowThreshold),
                    String.valueOf(maxSlow),
                    String.valueOf(blockDuration),
                    String.valueOf(requestTimeMs)
            );

            if (result != null) {
                switch (result.intValue()) {
                    case 2:
                        log.warn("Honeypot triggered, client blocked: {}", clientIdentifier);
                        return new HoneypotResult(true, true);
                    case 1:
                        if (requestTimeMs > slowThreshold) {
                            log.info("Honeypot recorded slow request from: {}, time: {}ms", clientIdentifier, requestTimeMs);
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
}

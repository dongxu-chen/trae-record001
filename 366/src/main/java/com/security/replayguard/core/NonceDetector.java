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
public class NonceDetector {

    private static final String KEY_PREFIX = "replay:nonce:";

    private final StringRedisTemplate redisTemplate;
    private final RedisScript<Long> nonceCheckAndSetScript;
    private final ReplayGuardProperties properties;
    private final RequestHasher requestHasher;

    public boolean isReplayAttack(String deviceFingerprint, String nonce, String timestamp) {
        if (nonce == null || nonce.isEmpty()) {
            return false;
        }

        String nonceHash = requestHasher.computeNonceHash(deviceFingerprint, nonce, timestamp);
        String key = KEY_PREFIX + nonceHash;
        long expireSeconds = properties.getNonceExpireSeconds();

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    nonceCheckAndSetScript,
                    keys,
                    nonceHash,
                    String.valueOf(expireSeconds)
            );

            if (result != null && result == 1) {
                log.debug("Nonce check passed for: {}", nonceHash);
                return false;
            } else {
                log.warn("Nonce replay detected for: {}", nonceHash);
                return true;
            }
        } catch (Exception e) {
            log.error("Nonce check error for: {}", nonceHash, e);
            return false;
        }
    }

    public boolean validateTimestamp(String timestampStr, long maxDriftSeconds) {
        if (timestampStr == null || timestampStr.isEmpty()) {
            return false;
        }

        try {
            long timestamp = Long.parseLong(timestampStr);
            long now = System.currentTimeMillis() / 1000;
            long diff = Math.abs(now - timestamp);

            return diff <= maxDriftSeconds;
        } catch (NumberFormatException e) {
            log.warn("Invalid timestamp format: {}", timestampStr);
            return false;
        }
    }
}

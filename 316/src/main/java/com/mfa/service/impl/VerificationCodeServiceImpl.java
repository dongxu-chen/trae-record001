package com.mfa.service.impl;

import com.mfa.service.VerificationCodeService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.security.SecureRandom;
import java.util.Random;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class VerificationCodeServiceImpl implements VerificationCodeService {

    private static final String CODE_KEY_PREFIX = "mfa:code:";
    private final Random random = new SecureRandom();

    private final RedisTemplate<String, Object> redisTemplate;

    @Override
    public String generateCode(String sessionId, String target, int length, int expireMinutes) {
        String code = generateRandomCode(length);
        String key = buildKey(sessionId, target);

        redisTemplate.opsForValue().set(key, code, expireMinutes, TimeUnit.MINUTES);
        log.debug("Generated verification code for session: {}, target: {}, expire: {} minutes",
                sessionId, maskTarget(target), expireMinutes);

        return code;
    }

    @Override
    public boolean verifyCode(String sessionId, String target, String code) {
        String key = buildKey(sessionId, target);
        String storedCode = (String) redisTemplate.opsForValue().get(key);

        if (storedCode == null) {
            log.debug("No verification code found for session: {}, target: {}", sessionId, maskTarget(target));
            return false;
        }

        boolean valid = storedCode.equals(code);
        if (valid) {
            redisTemplate.delete(key);
            log.debug("Verification code validated successfully for session: {}, target: {}",
                    sessionId, maskTarget(target));
        } else {
            log.debug("Verification code validation failed for session: {}, target: {}",
                    sessionId, maskTarget(target));
        }

        return valid;
    }

    @Override
    public void invalidateCode(String sessionId, String target) {
        String key = buildKey(sessionId, target);
        redisTemplate.delete(key);
        log.debug("Invalidated verification code for session: {}, target: {}", sessionId, maskTarget(target));
    }

    @Override
    public String getStoredCode(String sessionId, String target) {
        String key = buildKey(sessionId, target);
        return (String) redisTemplate.opsForValue().get(key);
    }

    private String generateRandomCode(int length) {
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            sb.append(random.nextInt(10));
        }
        return sb.toString();
    }

    private String buildKey(String sessionId, String target) {
        return CODE_KEY_PREFIX + sessionId + ":" + target;
    }

    private String maskTarget(String target) {
        if (target == null) {
            return null;
        }
        if (target.contains("@")) {
            int atIndex = target.indexOf("@");
            String username = target.substring(0, atIndex);
            String domain = target.substring(atIndex);
            if (username.length() <= 2) {
                return "*" + domain;
            }
            return username.charAt(0) + "***" + username.charAt(username.length() - 1) + domain;
        } else {
            if (target.length() <= 4) {
                return "****";
            }
            return target.substring(0, 3) + "****" + target.substring(target.length() - 4);
        }
    }
}

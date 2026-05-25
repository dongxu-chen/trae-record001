package com.riskcontrol.redis.service;

import org.redisson.api.RRateLimiter;
import org.redisson.api.RateIntervalUnit;
import org.redisson.api.RateType;
import org.redisson.api.RedissonClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class RateLimitingService {

    private static final Logger logger = LoggerFactory.getLogger(RateLimitingService.class);

    private static final String RATE_LIMITER_PREFIX = "risk:ratelimit:";

    private final RedissonClient redissonClient;

    @Autowired
    public RateLimitingService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public boolean tryAcquire(String key, int limit, int windowSeconds) {
        String fullKey = RATE_LIMITER_PREFIX + key;

        RRateLimiter rateLimiter = redissonClient.getRateLimiter(fullKey);
        rateLimiter.trySetRate(RateType.OVERALL, limit, windowSeconds, RateIntervalUnit.SECONDS);

        boolean acquired = rateLimiter.tryAcquire();
        if (!acquired) {
            logger.warn("Rate limit exceeded for key: {}, limit: {}/{}s", key, limit, windowSeconds);
        }
        return acquired;
    }

    public boolean tryAcquireLogin(String ipAddress) {
        return tryAcquire("login:ip:" + ipAddress, 10, 60);
    }

    public boolean tryAcquireLoginPerAccount(String account) {
        return tryAcquire("login:account:" + account, 5, 60);
    }

    public boolean tryAcquireRegister(String ipAddress) {
        return tryAcquire("register:ip:" + ipAddress, 5, 3600);
    }

    public boolean tryAcquirePasswordChange(String userId) {
        return tryAcquire("password:change:" + userId, 3, 3600);
    }

    public long getRemainingPermits(String key, int limit, int windowSeconds) {
        String fullKey = RATE_LIMITER_PREFIX + key;

        RRateLimiter rateLimiter = redissonClient.getRateLimiter(fullKey);
        rateLimiter.trySetRate(RateType.OVERALL, limit, windowSeconds, RateIntervalUnit.SECONDS);

        return rateLimiter.availablePermits();
    }

    public void resetRateLimit(String key) {
        String fullKey = RATE_LIMITER_PREFIX + key;
        redissonClient.getRateLimiter(fullKey).delete();
        logger.debug("Reset rate limit for key: {}", key);
    }
}

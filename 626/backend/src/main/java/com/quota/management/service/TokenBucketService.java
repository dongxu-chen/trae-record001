package com.quota.management.service;

import com.quota.management.algorithm.TokenBucket;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TokenBucketService {

    private static final String TOKEN_BUCKET_PREFIX = "quota:token-bucket:";
    private static final String DISTRIBUTED_LOCK_PREFIX = "quota:lock:";
    private static final String MINUTE_SUFFIX = ":minute";
    private static final String HOUR_SUFFIX = ":hour";
    private static final String DAY_SUFFIX = ":day";

    private static final long LOCK_WAIT_TIME = 3;
    private static final long LOCK_LEASE_TIME = 10;
    private static final int OPTIMISTIC_LOCK_RETRY_MAX = 3;

    private final RedisTemplate<String, Object> redisTemplate;

    public TokenBucket createBucket(String tenantId, String granularity, long capacity, long refillRate) {
        String key = buildKey(tenantId, granularity);
        TokenBucket bucket = TokenBucket.builder()
                .key(key)
                .capacity(capacity)
                .tokens(capacity)
                .refillRate(refillRate)
                .lastRefillTime(System.currentTimeMillis())
                .granularity(granularity)
                .version(0)
                .build();
        saveBucket(bucket, granularity);
        return bucket;
    }

    public TokenBucket getBucket(String tenantId, String granularity) {
        String key = buildKey(tenantId, granularity);
        Object obj = redisTemplate.opsForValue().get(key);
        if (obj instanceof TokenBucket) {
            return (TokenBucket) obj;
        }
        return null;
    }

    public void saveBucket(TokenBucket bucket, String granularity) {
        long ttl = getTTLForGranularity(granularity);
        redisTemplate.opsForValue().set(bucket.getKey(), bucket, ttl, TimeUnit.SECONDS);
    }

    public boolean tryConsume(String tenantId, String granularity, long tokens) {
        TokenBucket bucket = getBucket(tenantId, granularity);
        if (bucket == null) {
            log.warn("Token bucket not found for tenant: {}, granularity: {}", tenantId, granularity);
            return false;
        }
        boolean consumed = bucket.tryConsume(tokens);
        if (consumed) {
            saveBucket(bucket, granularity);
        }
        return consumed;
    }

    public long getAvailableTokens(String tenantId, String granularity) {
        TokenBucket bucket = getBucket(tenantId, granularity);
        if (bucket == null) {
            return 0;
        }
        return bucket.getAvailableTokens();
    }

    public void addTokens(String tenantId, String granularity, long amount) {
        TokenBucket bucket = getBucket(tenantId, granularity);
        if (bucket != null) {
            bucket.addTokens(amount);
            saveBucket(bucket, granularity);
        }
    }

    public void resetBucket(String tenantId, String granularity) {
        TokenBucket bucket = getBucket(tenantId, granularity);
        if (bucket != null) {
            bucket.reset();
            saveBucket(bucket, granularity);
        }
    }

    public void deleteBucket(String tenantId, String granularity) {
        String key = buildKey(tenantId, granularity);
        redisTemplate.delete(key);
    }

    public PreConsumeResult preConsumeWithDistributedLock(String tenantId, String granularity, long amount) {
        String lockKey = DISTRIBUTED_LOCK_PREFIX + tenantId + ":" + granularity;
        String lockValue = UUID.randomUUID().toString();

        boolean locked = tryLock(lockKey, lockValue, LOCK_LEASE_TIME);
        if (!locked) {
            log.warn("Failed to acquire distributed lock for tenant: {}, granularity: {}", tenantId, granularity);
            return PreConsumeResult.fail("LOCK_FAILED");
        }

        try {
            return preConsumeWithOptimisticLock(tenantId, granularity, amount);
        } finally {
            unlock(lockKey, lockValue);
        }
    }

    private PreConsumeResult preConsumeWithOptimisticLock(String tenantId, String granularity, long amount) {
        for (int retry = 0; retry < OPTIMISTIC_LOCK_RETRY_MAX; retry++) {
            TokenBucket bucket = getBucket(tenantId, granularity);
            if (bucket == null) {
                return PreConsumeResult.fail("BUCKET_NOT_FOUND");
            }

            TokenBucket.TokenBucketSnapshot snapshot = bucket.refillAndGetSnapshot();
            long expectedVersion = snapshot.getVersion();
            long currentTokens = snapshot.getTokens();

            if (currentTokens < amount) {
                return PreConsumeResult.fail("INSUFFICIENT_QUOTA");
            }

            boolean success = bucket.tryConsumeWithVersion(amount, expectedVersion);
            if (success) {
                TokenBucket.TokenBucketSnapshot newSnapshot = bucket.refillAndGetSnapshot();
                saveBucket(bucket, granularity);

                log.info("Pre-consumed {} quota for tenant {} (granularity: {}, version: {}->{})",
                        amount, tenantId, granularity, expectedVersion, newSnapshot.getVersion());

                return PreConsumeResult.success(
                        newSnapshot.getVersion(),
                        newSnapshot.getTokens(),
                        expectedVersion
                );
            }

            log.debug("Optimistic lock conflict for tenant: {}, granularity: {}, retry: {}",
                    tenantId, granularity, retry + 1);

            try {
                Thread.sleep(50 + (long) (Math.random() * 100));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return PreConsumeResult.fail("INTERRUPTED");
            }
        }

        log.warn("Optimistic lock retry exhausted for tenant: {}, granularity: {}", tenantId, granularity);
        return PreConsumeResult.fail("OPTIMISTIC_LOCK_RETRY_EXHAUSTED");
    }

    public boolean releasePreConsumedWithDistributedLock(String tenantId, String granularity, long amount) {
        String lockKey = DISTRIBUTED_LOCK_PREFIX + tenantId + ":" + granularity;
        String lockValue = UUID.randomUUID().toString();

        boolean locked = tryLock(lockKey, lockValue, LOCK_LEASE_TIME);
        if (!locked) {
            log.warn("Failed to acquire distributed lock for release, tenant: {}, granularity: {}", tenantId, granularity);
            return false;
        }

        try {
            for (int retry = 0; retry < OPTIMISTIC_LOCK_RETRY_MAX; retry++) {
                TokenBucket bucket = getBucket(tenantId, granularity);
                if (bucket == null) {
                    return false;
                }

                long expectedVersion = bucket.getVersion();
                bucket.addTokens(amount);

                if (bucket.getVersion() != expectedVersion + 1) {
                    continue;
                }

                saveBucket(bucket, granularity);
                log.info("Released {} pre-consumed quota for tenant {} (granularity: {})",
                        amount, tenantId, granularity);
                return true;
            }
            return false;
        } finally {
            unlock(lockKey, lockValue);
        }
    }

    public boolean confirmPreConsumedWithDistributedLock(String tenantId, String granularity, long amount) {
        String lockKey = DISTRIBUTED_LOCK_PREFIX + tenantId + ":" + granularity;
        String lockValue = UUID.randomUUID().toString();

        boolean locked = tryLock(lockKey, lockValue, LOCK_LEASE_TIME);
        if (!locked) {
            return false;
        }

        try {
            log.info("Confirmed {} pre-consumed quota for tenant {} (granularity: {})",
                    amount, tenantId, granularity);
            return true;
        } finally {
            unlock(lockKey, lockValue);
        }
    }

    private boolean tryLock(String lockKey, String lockValue, long leaseTime) {
        Boolean result = redisTemplate.opsForValue()
                .setIfAbsent(lockKey, lockValue, leaseTime, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(result);
    }

    private void unlock(String lockKey, String lockValue) {
        String luaScript = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                "return redis.call('del', KEYS[1]) " +
                "else " +
                "return 0 " +
                "end";
        DefaultRedisScript<Long> redisScript = new DefaultRedisScript<>(luaScript, Long.class);
        redisTemplate.execute(redisScript, Collections.singletonList(lockKey), lockValue);
    }

    private String buildKey(String tenantId, String granularity) {
        String suffix;
        switch (granularity.toLowerCase()) {
            case "minute":
                suffix = MINUTE_SUFFIX;
                break;
            case "hour":
                suffix = HOUR_SUFFIX;
                break;
            case "day":
                suffix = DAY_SUFFIX;
                break;
            default:
                suffix = ":" + granularity;
        }
        return TOKEN_BUCKET_PREFIX + tenantId + suffix;
    }

    private long getTTLForGranularity(String granularity) {
        switch (granularity.toLowerCase()) {
            case "minute":
                return 120;
            case "hour":
                return 3600 * 2;
            case "day":
                return 3600 * 24 * 2;
            default:
                return 3600;
        }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class PreConsumeResult {
        private boolean success;
        private String failReason;
        private long newVersion;
        private long remainingTokens;
        private long previousVersion;

        public static PreConsumeResult success(long newVersion, long remainingTokens, long previousVersion) {
            return PreConsumeResult.builder()
                    .success(true)
                    .newVersion(newVersion)
                    .remainingTokens(remainingTokens)
                    .previousVersion(previousVersion)
                    .build();
        }

        public static PreConsumeResult fail(String reason) {
            return PreConsumeResult.builder()
                    .success(false)
                    .failReason(reason)
                    .build();
        }
    }
}

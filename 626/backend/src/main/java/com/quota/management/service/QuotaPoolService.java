package com.quota.management.service;

import com.quota.management.entity.PoolMemberAllocation;
import com.quota.management.entity.QuotaPool;
import com.quota.management.service.TokenBucketService.PreConsumeResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuotaPoolService {

    private static final String POOL_PREFIX = "quota:pool:";
    private static final String POOL_SET_KEY = "quota:pools:all";
    private static final String POOL_MEMBER_PREFIX = "quota:pool:member:";
    private static final String POOL_LOCK_PREFIX = "quota:pool:lock:";

    private final RedisTemplate<String, Object> redisTemplate;
    private final TokenBucketService tokenBucketService;
    private final QuotaManagementService quotaManagementService;

    public QuotaPool createPool(QuotaPool pool) {
        pool.setPoolId(UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        pool.setCreatedAt(LocalDateTime.now());
        pool.setUpdatedAt(LocalDateTime.now());
        if (pool.getEnabled() == null) {
            pool.setEnabled(true);
        }
        if (pool.getAllocationStrategy() == null) {
            pool.setAllocationStrategy(QuotaPool.AllocationStrategy.FAIR_QUEUE);
        }

        String key = POOL_PREFIX + pool.getPoolId();
        redisTemplate.opsForValue().set(key, pool);
        redisTemplate.opsForSet().add(POOL_SET_KEY, pool.getPoolId());

        initPoolTokenBuckets(pool);

        log.info("Created quota pool: {} ({})", pool.getPoolName(), pool.getPoolId());
        return pool;
    }

    private void initPoolTokenBuckets(QuotaPool pool) {
        if (pool.getMinuteCapacity() != null && pool.getMinuteCapacity() > 0) {
            tokenBucketService.createBucket("pool:" + pool.getPoolId(), "minute",
                    pool.getMinuteCapacity(), pool.getMinuteCapacity() / 60);
        }
        if (pool.getHourCapacity() != null && pool.getHourCapacity() > 0) {
            tokenBucketService.createBucket("pool:" + pool.getPoolId(), "hour",
                    pool.getHourCapacity(), pool.getHourCapacity() / 3600);
        }
        if (pool.getDayCapacity() != null && pool.getDayCapacity() > 0) {
            tokenBucketService.createBucket("pool:" + pool.getPoolId(), "day",
                    pool.getDayCapacity(), pool.getDayCapacity() / 86400);
        }
    }

    public QuotaPool getPool(String poolId) {
        String key = POOL_PREFIX + poolId;
        Object obj = redisTemplate.opsForValue().get(key);
        if (obj instanceof QuotaPool) {
            return (QuotaPool) obj;
        }
        return null;
    }

    public QuotaPool updatePool(QuotaPool pool) {
        QuotaPool existing = getPool(pool.getPoolId());
        if (existing == null) {
            throw new RuntimeException("Pool not found");
        }

        pool.setCreatedAt(existing.getCreatedAt());
        pool.setUpdatedAt(LocalDateTime.now());

        String key = POOL_PREFIX + pool.getPoolId();
        redisTemplate.opsForValue().set(key, pool);

        tokenBucketService.deleteBucket("pool:" + pool.getPoolId(), "minute");
        tokenBucketService.deleteBucket("pool:" + pool.getPoolId(), "hour");
        tokenBucketService.deleteBucket("pool:" + pool.getPoolId(), "day");
        initPoolTokenBuckets(pool);

        log.info("Updated quota pool: {}", pool.getPoolId());
        return pool;
    }

    public void deletePool(String poolId) {
        String key = POOL_PREFIX + poolId;
        redisTemplate.delete(key);
        redisTemplate.opsForSet().remove(POOL_SET_KEY, poolId);

        tokenBucketService.deleteBucket("pool:" + poolId, "minute");
        tokenBucketService.deleteBucket("pool:" + poolId, "hour");
        tokenBucketService.deleteBucket("pool:" + poolId, "day");

        Set<String> memberKeys = redisTemplate.keys(POOL_MEMBER_PREFIX + poolId + ":*");
        if (memberKeys != null) {
            redisTemplate.delete(memberKeys);
        }

        log.info("Deleted quota pool: {}", poolId);
    }

    public List<QuotaPool> getAllPools() {
        Set<Object> poolIds = redisTemplate.opsForSet().members(POOL_SET_KEY);
        if (poolIds == null || poolIds.isEmpty()) {
            return List.of();
        }

        return poolIds.stream()
                .map(id -> getPool(String.valueOf(id)))
                .filter(p -> p != null)
                .collect(Collectors.toList());
    }

    public void addMember(String poolId, String tenantId, Double weight) {
        QuotaPool pool = getPool(poolId);
        if (pool == null) {
            throw new RuntimeException("Pool not found");
        }

        String lockKey = POOL_LOCK_PREFIX + poolId;
        String lockValue = UUID.randomUUID().toString();
        if (!tryLock(lockKey, lockValue, 10)) {
            throw new RuntimeException("Failed to acquire pool lock");
        }

        try {
            Set<String> members = pool.getMemberTenants();
            if (members == null) {
                members = new HashSet<>();
            }
            members.add(tenantId);
            pool.setMemberTenants(members);

            String key = POOL_PREFIX + poolId;
            redisTemplate.opsForValue().set(key, pool);

            PoolMemberAllocation allocation = PoolMemberAllocation.builder()
                    .poolId(poolId)
                    .tenantId(tenantId)
                    .weight(weight != null ? weight : 1.0)
                    .priority(0L)
                    .lastAllocatedAt(System.currentTimeMillis())
                    .build();

            String memberKey = POOL_MEMBER_PREFIX + poolId + ":" + tenantId;
            redisTemplate.opsForValue().set(memberKey, allocation);

            log.info("Added tenant {} to pool {}", tenantId, poolId);
        } finally {
            unlock(lockKey, lockValue);
        }
    }

    public void removeMember(String poolId, String tenantId) {
        QuotaPool pool = getPool(poolId);
        if (pool == null) {
            throw new RuntimeException("Pool not found");
        }

        String lockKey = POOL_LOCK_PREFIX + poolId;
        String lockValue = UUID.randomUUID().toString();
        if (!tryLock(lockKey, lockValue, 10)) {
            throw new RuntimeException("Failed to acquire pool lock");
        }

        try {
            Set<String> members = pool.getMemberTenants();
            if (members != null) {
                members.remove(tenantId);
            }
            pool.setMemberTenants(members);

            String key = POOL_PREFIX + poolId;
            redisTemplate.opsForValue().set(key, pool);

            String memberKey = POOL_MEMBER_PREFIX + poolId + ":" + tenantId;
            redisTemplate.delete(memberKey);

            log.info("Removed tenant {} from pool {}", tenantId, poolId);
        } finally {
            unlock(lockKey, lockValue);
        }
    }

    public PreConsumeResult consumeFromPool(String poolId, String tenantId, String granularity, long amount) {
        QuotaPool pool = getPool(poolId);
        if (pool == null || !pool.getEnabled()) {
            return PreConsumeResult.fail("POOL_NOT_AVAILABLE");
        }

        if (pool.getMemberTenants() == null || !pool.getMemberTenants().contains(tenantId)) {
            return PreConsumeResult.fail("NOT_A_MEMBER");
        }

        String memberKey = POOL_MEMBER_PREFIX + poolId + ":" + tenantId;
        PoolMemberAllocation allocation = (PoolMemberAllocation) redisTemplate.opsForValue().get(memberKey);
        if (allocation == null) {
            return PreConsumeResult.fail("MEMBER_ALLOCATION_NOT_FOUND");
        }

        long maxPerMember = getMaxPerMember(pool, granularity);
        if (maxPerMember > 0) {
            long used = getMemberUsed(allocation, granularity);
            if (used + amount > maxPerMember) {
                return PreConsumeResult.fail("MEMBER_QUOTA_EXCEEDED");
            }
        }

        PreConsumeResult result = tokenBucketService.preConsumeWithDistributedLock(
                "pool:" + poolId, granularity, amount);

        if (result.isSuccess()) {
            updateMemberUsed(allocation, granularity, amount);
            redisTemplate.opsForValue().set(memberKey, allocation);
        }

        return result;
    }

    private long getMaxPerMember(QuotaPool pool, String granularity) {
        switch (granularity.toLowerCase()) {
            case "minute":
                return pool.getMaxPerMemberMinute() != null ? pool.getMaxPerMemberMinute() : 0;
            case "hour":
                return pool.getMaxPerMemberHour() != null ? pool.getMaxPerMemberHour() : 0;
            case "day":
                return pool.getMaxPerMemberDay() != null ? pool.getMaxPerMemberDay() : 0;
            default:
                return 0;
        }
    }

    private long getMemberUsed(PoolMemberAllocation allocation, String granularity) {
        switch (granularity.toLowerCase()) {
            case "minute":
                return allocation.getMinuteUsed() != null ? allocation.getMinuteUsed() : 0;
            case "hour":
                return allocation.getHourUsed() != null ? allocation.getHourUsed() : 0;
            case "day":
                return allocation.getDayUsed() != null ? allocation.getDayUsed() : 0;
            default:
                return 0;
        }
    }

    private void updateMemberUsed(PoolMemberAllocation allocation, String granularity, long amount) {
        switch (granularity.toLowerCase()) {
            case "minute":
                allocation.setMinuteUsed((allocation.getMinuteUsed() != null ? allocation.getMinuteUsed() : 0) + amount);
                break;
            case "hour":
                allocation.setHourUsed((allocation.getHourUsed() != null ? allocation.getHourUsed() : 0) + amount);
                break;
            case "day":
                allocation.setDayUsed((allocation.getDayUsed() != null ? allocation.getDayUsed() : 0) + amount);
                break;
        }
        allocation.setLastAllocatedAt(System.currentTimeMillis());
    }

    public List<PoolMemberAllocation> getPoolMembers(String poolId) {
        Set<String> keys = redisTemplate.keys(POOL_MEMBER_PREFIX + poolId + ":*");
        if (keys == null || keys.isEmpty()) {
            return List.of();
        }

        List<PoolMemberAllocation> members = new ArrayList<>();
        for (String key : keys) {
            Object obj = redisTemplate.opsForValue().get(key);
            if (obj instanceof PoolMemberAllocation) {
                members.add((PoolMemberAllocation) obj);
            }
        }
        return members;
    }

    public Map<String, Object> getPoolStats(String poolId) {
        QuotaPool pool = getPool(poolId);
        if (pool == null) {
            return null;
        }

        Map<String, Object> stats = new HashMap<>();
        stats.put("pool", pool);

        long minuteAvail = tokenBucketService.getAvailableTokens("pool:" + poolId, "minute");
        long hourAvail = tokenBucketService.getAvailableTokens("pool:" + poolId, "hour");
        long dayAvail = tokenBucketService.getAvailableTokens("pool:" + poolId, "day");

        Map<String, Object> usage = new HashMap<>();
        usage.put("minuteUsed", pool.getMinuteCapacity() - minuteAvail);
        usage.put("hourUsed", pool.getHourCapacity() - hourAvail);
        usage.put("dayUsed", pool.getDayCapacity() - dayAvail);
        usage.put("minuteRemaining", minuteAvail);
        usage.put("hourRemaining", hourAvail);
        usage.put("dayRemaining", dayAvail);
        usage.put("minuteUsageRate", (double) (pool.getMinuteCapacity() - minuteAvail) / pool.getMinuteCapacity());
        usage.put("hourUsageRate", (double) (pool.getHourCapacity() - hourAvail) / pool.getHourCapacity());
        usage.put("dayUsageRate", (double) (pool.getDayCapacity() - dayAvail) / pool.getDayCapacity());

        stats.put("usage", usage);
        stats.put("members", getPoolMembers(poolId));

        return stats;
    }

    @Scheduled(cron = "0 * * * * ?")
    public void resetMinuteUsage() {
        Set<Object> poolIds = redisTemplate.opsForSet().members(POOL_SET_KEY);
        if (poolIds == null) return;

        for (Object poolIdObj : poolIds) {
            String poolId = String.valueOf(poolIdObj);
            Set<String> memberKeys = redisTemplate.keys(POOL_MEMBER_PREFIX + poolId + ":*");
            if (memberKeys != null) {
                for (String key : memberKeys) {
                    Object obj = redisTemplate.opsForValue().get(key);
                    if (obj instanceof PoolMemberAllocation) {
                        PoolMemberAllocation alloc = (PoolMemberAllocation) obj;
                        alloc.setMinuteUsed(0L);
                        redisTemplate.opsForValue().set(key, alloc);
                    }
                }
            }
        }
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void resetHourUsage() {
        Set<Object> poolIds = redisTemplate.opsForSet().members(POOL_SET_KEY);
        if (poolIds == null) return;

        for (Object poolIdObj : poolIds) {
            String poolId = String.valueOf(poolIdObj);
            Set<String> memberKeys = redisTemplate.keys(POOL_MEMBER_PREFIX + poolId + ":*");
            if (memberKeys != null) {
                for (String key : memberKeys) {
                    Object obj = redisTemplate.opsForValue().get(key);
                    if (obj instanceof PoolMemberAllocation) {
                        PoolMemberAllocation alloc = (PoolMemberAllocation) obj;
                        alloc.setHourUsed(0L);
                        redisTemplate.opsForValue().set(key, alloc);
                    }
                }
            }
        }
    }

    @Scheduled(cron = "0 0 0 * * ?")
    public void resetDayUsage() {
        Set<Object> poolIds = redisTemplate.opsForSet().members(POOL_SET_KEY);
        if (poolIds == null) return;

        for (Object poolIdObj : poolIds) {
            String poolId = String.valueOf(poolIdObj);
            Set<String> memberKeys = redisTemplate.keys(POOL_MEMBER_PREFIX + poolId + ":*");
            if (memberKeys != null) {
                for (String key : memberKeys) {
                    Object obj = redisTemplate.opsForValue().get(key);
                    if (obj instanceof PoolMemberAllocation) {
                        PoolMemberAllocation alloc = (PoolMemberAllocation) obj;
                        alloc.setDayUsed(0L);
                        redisTemplate.opsForValue().set(key, alloc);
                    }
                }
            }
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
        org.springframework.data.redis.core.script.DefaultRedisScript<Long> redisScript =
                new org.springframework.data.redis.core.script.DefaultRedisScript<>(luaScript, Long.class);
        redisTemplate.execute(redisScript, java.util.Collections.singletonList(lockKey), lockValue);
    }
}

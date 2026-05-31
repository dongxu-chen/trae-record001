package com.distributed.lock.redis;

import org.redisson.api.RedissonClient;

public class RedisLockFactory {

    private final RedissonClient redissonClient;
    private final String applicationName;

    public RedisLockFactory(RedissonClient redissonClient, String applicationName) {
        this.redissonClient = redissonClient;
        this.applicationName = applicationName;
    }

    public RedisDistributedLock getLock(String lockKey) {
        return new RedisDistributedLock(lockKey, applicationName, redissonClient);
    }
}
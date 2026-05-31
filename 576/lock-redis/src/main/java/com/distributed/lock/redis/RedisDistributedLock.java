package com.distributed.lock.redis;

import com.distributed.lock.core.AbstractDistributedLock;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;

import java.util.concurrent.TimeUnit;

public class RedisDistributedLock extends AbstractDistributedLock {

    private final RLock rLock;
    private final RedissonClient redissonClient;

    public RedisDistributedLock(String lockKey, String applicationName, RedissonClient redissonClient) {
        super(lockKey, applicationName);
        this.redissonClient = redissonClient;
        this.rLock = redissonClient.getLock(lockKey);
    }

    @Override
    protected boolean doTryLock(long waitTime, long leaseTime, TimeUnit unit) throws InterruptedException {
        return rLock.tryLock(waitTime, leaseTime, unit);
    }

    @Override
    protected void doLock(long leaseTime, TimeUnit unit) {
        rLock.lock(leaseTime, unit);
    }

    @Override
    protected void doUnlock() {
        if (rLock.isHeldByCurrentThread()) {
            rLock.unlock();
        }
    }

    @Override
    public boolean isHeldByCurrentThread() {
        return rLock.isHeldByCurrentThread();
    }

    @Override
    public boolean isLocked() {
        return rLock.isLocked();
    }

    @Override
    public String getLockType() {
        return "REDIS";
    }

    public RLock getRLock() {
        return rLock;
    }
}
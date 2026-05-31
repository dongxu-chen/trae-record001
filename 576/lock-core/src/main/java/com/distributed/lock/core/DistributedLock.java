package com.distributed.lock.core;

import java.util.concurrent.TimeUnit;

public interface DistributedLock {

    boolean tryLock(long waitTime, long leaseTime, TimeUnit unit) throws InterruptedException;

    void lock(long leaseTime, TimeUnit unit);

    void unlock();

    boolean isHeldByCurrentThread();

    boolean isLocked();

    String getLockKey();

    String getLockType();
}
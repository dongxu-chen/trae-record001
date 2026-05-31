package com.distributed.lock.zookeeper;

import com.distributed.lock.core.AbstractDistributedLock;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.recipes.locks.InterProcessMutex;

import java.util.concurrent.TimeUnit;

public class ZkDistributedLock extends AbstractDistributedLock {

    private static final String LOCK_BASE_PATH = "/distributed-locks";
    private final InterProcessMutex interProcessMutex;
    private final ThreadLocal<Boolean> isLockedByThread = new ThreadLocal<>();

    public ZkDistributedLock(String lockKey, String applicationName, CuratorFramework curatorFramework) {
        super(lockKey, applicationName);
        String lockPath = LOCK_BASE_PATH + "/" + lockKey;
        this.interProcessMutex = new InterProcessMutex(curatorFramework, lockPath);
    }

    @Override
    protected boolean doTryLock(long waitTime, long leaseTime, TimeUnit unit) throws InterruptedException {
        try {
            boolean acquired = interProcessMutex.acquire(waitTime, unit);
            if (acquired) {
                isLockedByThread.set(true);
            }
            return acquired;
        } catch (Exception e) {
            throw new RuntimeException("Failed to acquire ZooKeeper lock", e);
        }
    }

    @Override
    protected void doLock(long leaseTime, TimeUnit unit) {
        try {
            interProcessMutex.acquire();
            isLockedByThread.set(true);
        } catch (Exception e) {
            throw new RuntimeException("Failed to acquire ZooKeeper lock", e);
        }
    }

    @Override
    protected void doUnlock() {
        try {
            if (isHeldByCurrentThread()) {
                interProcessMutex.release();
                isLockedByThread.remove();
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to release ZooKeeper lock", e);
        }
    }

    @Override
    public boolean isHeldByCurrentThread() {
        Boolean locked = isLockedByThread.get();
        return locked != null && locked && interProcessMutex.isAcquiredInThisProcess();
    }

    @Override
    public boolean isLocked() {
        return interProcessMutex.isAcquiredInThisProcess();
    }

    @Override
    public String getLockType() {
        return "ZOOKEEPER";
    }
}
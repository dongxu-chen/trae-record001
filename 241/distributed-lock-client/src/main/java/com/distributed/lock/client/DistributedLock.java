package com.distributed.lock.client;

import com.distributed.lock.proto.LockResponse;
import com.distributed.lock.proto.LockType;
import com.distributed.lock.proto.TryLockResponse;
import com.distributed.lock.proto.UnlockResponse;

import java.util.concurrent.Callable;

public class DistributedLock implements AutoCloseable {
    
    private final DistributedLockClient client;
    private final String lockName;
    private final LockType lockType;
    private final boolean reentrant;
    private String currentLockToken;
    private volatile boolean locked = false;

    public DistributedLock(DistributedLockClient client, String lockName) {
        this(client, lockName, LockType.EXCLUSIVE, true);
    }

    public DistributedLock(DistributedLockClient client, String lockName, LockType lockType, boolean reentrant) {
        this.client = client;
        this.lockName = lockName;
        this.lockType = lockType;
        this.reentrant = reentrant;
    }

    public void lock() {
        LockResponse response = client.lock(lockName, lockType, reentrant);
        if (response.getSuccess()) {
            this.currentLockToken = response.getLockToken();
            this.locked = true;
        } else {
            throw new RuntimeException("Failed to acquire lock: " + response.getMessage());
        }
    }

    public boolean tryLock() {
        TryLockResponse response = client.tryLock(lockName, lockType, reentrant);
        if (response.getSuccess()) {
            this.currentLockToken = response.getLockToken();
            this.locked = true;
            return true;
        }
        return false;
    }

    public void unlock() {
        if (currentLockToken != null && locked) {
            try {
                UnlockResponse response = client.unlock(lockName, currentLockToken);
                if (!response.getSuccess()) {
                    throw new RuntimeException("Failed to release lock: " + response.getMessage());
                }
            } finally {
                this.locked = false;
            }
        }
    }

    public <T> T executeWithLock(Callable<T> callable) throws Exception {
        lock();
        try {
            return callable.call();
        } finally {
            unlock();
        }
    }

    public void executeWithLock(Runnable runnable) {
        lock();
        try {
            runnable.run();
        } finally {
            unlock();
        }
    }

    public <T> T tryExecuteWithLock(Callable<T> callable, T defaultValue) throws Exception {
        if (tryLock()) {
            try {
                return callable.call();
            } finally {
                unlock();
            }
        }
        return defaultValue;
    }

    public boolean isLocked() {
        return locked;
    }

    public String getLockName() {
        return lockName;
    }

    public String getCurrentLockToken() {
        return currentLockToken;
    }

    @Override
    public void close() {
        unlock();
    }
}
package com.distributed.lock.server.lock;

import com.distributed.lock.proto.LockType;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

public class LockInfo {
    
    private final String lockName;
    private final Map<String, LockHolder> holders;
    private final List<Waiter> waitQueue;
    private final AtomicInteger readLockCount;
    private final AtomicInteger waitingWriteLockCount;
    private volatile LockType currentLockType;
    private volatile long leaseExpireTime;
    private volatile long leaseId;

    public LockInfo(String lockName) {
        this.lockName = lockName;
        this.holders = new ConcurrentHashMap<>();
        this.waitQueue = new CopyOnWriteArrayList<>();
        this.readLockCount = new AtomicInteger(0);
        this.waitingWriteLockCount = new AtomicInteger(0);
        this.currentLockType = null;
    }

    public String getLockName() {
        return lockName;
    }

    public Map<String, LockHolder> getHolders() {
        return holders;
    }

    public void addHolder(String clientId, String lockToken, LockType lockType, long leaseId, long ttlSeconds) {
        LockHolder holder = new LockHolder(clientId, lockToken, lockType, leaseId, System.currentTimeMillis() + ttlSeconds * 1000);
        holders.put(clientId, holder);
        this.currentLockType = lockType;
        this.leaseId = leaseId;
        if (lockType == LockType.READ) {
            readLockCount.incrementAndGet();
        }
    }

    public void removeHolder(String clientId) {
        LockHolder holder = holders.remove(clientId);
        if (holder != null && holder.getLockType() == LockType.READ) {
            readLockCount.decrementAndGet();
        }
        if (holders.isEmpty()) {
            currentLockType = null;
            leaseId = 0;
        }
    }

    public LockHolder getHolder(String clientId) {
        return holders.get(clientId);
    }

    public boolean isHeldBy(String clientId) {
        return holders.containsKey(clientId);
    }

    public List<Waiter> getWaitQueue() {
        return waitQueue;
    }

    public void addWaiter(Waiter waiter) {
        waitQueue.add(waiter);
        if (waiter.getLockType() == LockType.WRITE || waiter.getLockType() == LockType.EXCLUSIVE) {
            waitingWriteLockCount.incrementAndGet();
        }
    }

    public void removeWaiter(Waiter waiter) {
        waitQueue.remove(waiter);
        if (waiter.getLockType() == LockType.WRITE || waiter.getLockType() == LockType.EXCLUSIVE) {
            waitingWriteLockCount.decrementAndGet();
        }
    }

    public int getWaitQueueLength() {
        return waitQueue.size();
    }

    public boolean hasWaitingWriteLock() {
        return waitingWriteLockCount.get() > 0;
    }

    public int getWaitingWriteLockCount() {
        return waitingWriteLockCount.get();
    }

    public int getReadLockCount() {
        return readLockCount.get();
    }

    public LockType getCurrentLockType() {
        return currentLockType;
    }

    public boolean isLocked() {
        return !holders.isEmpty();
    }

    public boolean isWriteLocked() {
        return currentLockType == LockType.WRITE || currentLockType == LockType.EXCLUSIVE;
    }

    public boolean isReadLocked() {
        return currentLockType == LockType.READ;
    }

    public long getLeaseExpireTime() {
        return leaseExpireTime;
    }

    public void setLeaseExpireTime(long leaseExpireTime) {
        this.leaseExpireTime = leaseExpireTime;
    }

    public long getLeaseId() {
        return leaseId;
    }

    public int getHolderCount() {
        return holders.size();
    }

    public void updateHeartbeat(String clientId) {
        LockHolder holder = holders.get(clientId);
        if (holder != null) {
            holder.updateHeartbeat();
        }
    }

    public static class LockHolder {
        private final String clientId;
        private final String lockToken;
        private final LockType lockType;
        private final long leaseId;
        private final AtomicInteger holdCount;
        private volatile long expireTime;
        private final AtomicLong lastHeartbeatTime;

        public LockHolder(String clientId, String lockToken, LockType lockType, long leaseId, long expireTime) {
            this.clientId = clientId;
            this.lockToken = lockToken;
            this.lockType = lockType;
            this.leaseId = leaseId;
            this.expireTime = expireTime;
            this.holdCount = new AtomicInteger(1);
            this.lastHeartbeatTime = new AtomicLong(System.currentTimeMillis());
        }

        public String getClientId() {
            return clientId;
        }

        public String getLockToken() {
            return lockToken;
        }

        public LockType getLockType() {
            return lockType;
        }

        public long getLeaseId() {
            return leaseId;
        }

        public int incrementHoldCount() {
            return holdCount.incrementAndGet();
        }

        public int decrementHoldCount() {
            return holdCount.decrementAndGet();
        }

        public int getHoldCount() {
            return holdCount.get();
        }

        public long getExpireTime() {
            return expireTime;
        }

        public void setExpireTime(long expireTime) {
            this.expireTime = expireTime;
        }

        public boolean isExpired() {
            return System.currentTimeMillis() > expireTime;
        }

        public void updateHeartbeat() {
            lastHeartbeatTime.set(System.currentTimeMillis());
        }

        public long getLastHeartbeatTime() {
            return lastHeartbeatTime.get();
        }

        public boolean isHeartbeatExpired(long timeoutMs) {
            return System.currentTimeMillis() - lastHeartbeatTime.get() > timeoutMs;
        }
    }

    public static class Waiter {
        private final String clientId;
        private final LockType lockType;
        private final long timeoutMs;
        private final long createTime;
        private final Runnable onAcquired;

        public Waiter(String clientId, LockType lockType, long timeoutMs, Runnable onAcquired) {
            this.clientId = clientId;
            this.lockType = lockType;
            this.timeoutMs = timeoutMs;
            this.createTime = System.currentTimeMillis();
            this.onAcquired = onAcquired;
        }

        public String getClientId() {
            return clientId;
        }

        public LockType getLockType() {
            return lockType;
        }

        public long getTimeoutMs() {
            return timeoutMs;
        }

        public long getCreateTime() {
            return createTime;
        }

        public boolean isTimedOut() {
            return System.currentTimeMillis() - createTime > timeoutMs;
        }

        public void notifyAcquired() {
            if (onAcquired != null) {
                onAcquired.run();
            }
        }
    }
}
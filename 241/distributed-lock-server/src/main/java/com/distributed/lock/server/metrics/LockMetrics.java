package com.distributed.lock.server.metrics;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

public class LockMetrics {
    
    private final String lockName;
    private final LongAdder acquireCount;
    private final LongAdder totalWaitTimeMs;
    private final LongAdder totalHoldTimeMs;
    private final AtomicLong maxWaitTimeMs;
    private final AtomicLong maxHoldTimeMs;
    private final LongAdder totalWaiters;
    private final AtomicLong lastAcquireTime;
    private final AtomicLong lastReleaseTime;

    public LockMetrics(String lockName) {
        this.lockName = lockName;
        this.acquireCount = new LongAdder();
        this.totalWaitTimeMs = new LongAdder();
        this.totalHoldTimeMs = new LongAdder();
        this.maxWaitTimeMs = new AtomicLong(0);
        this.maxHoldTimeMs = new AtomicLong(0);
        this.totalWaiters = new LongAdder();
        this.lastAcquireTime = new AtomicLong(0);
        this.lastReleaseTime = new AtomicLong(0);
    }

    public void recordWaitTime(long waitTimeMs) {
        totalWaitTimeMs.add(waitTimeMs);
        maxWaitTimeMs.accumulateAndGet(waitTimeMs, Math::max);
        totalWaiters.increment();
    }

    public void recordHoldTime(long holdTimeMs) {
        totalHoldTimeMs.add(holdTimeMs);
        maxHoldTimeMs.accumulateAndGet(holdTimeMs, Math::max);
        acquireCount.increment();
        lastReleaseTime.set(System.currentTimeMillis());
    }

    public void recordAcquire() {
        lastAcquireTime.set(System.currentTimeMillis());
    }

    public String getLockName() {
        return lockName;
    }

    public long getAcquireCount() {
        return acquireCount.sum();
    }

    public double getAvgWaitTimeMs() {
        long waiters = totalWaiters.sum();
        return waiters > 0 ? (double) totalWaitTimeMs.sum() / waiters : 0.0;
    }

    public double getAvgHoldTimeMs() {
        long count = acquireCount.sum();
        return count > 0 ? (double) totalHoldTimeMs.sum() / count : 0.0;
    }

    public long getMaxWaitTimeMs() {
        return maxWaitTimeMs.get();
    }

    public long getMaxHoldTimeMs() {
        return maxHoldTimeMs.get();
    }

    public long getTotalWaiters() {
        return totalWaiters.sum();
    }

    public long getLastAcquireTime() {
        return lastAcquireTime.get();
    }

    public long getLastReleaseTime() {
        return lastReleaseTime.get();
    }

    public double getContentionScore() {
        double avgWait = getAvgWaitTimeMs();
        double avgHold = getAvgHoldTimeMs();
        long count = getAcquireCount();
        
        if (count == 0) {
            return 0.0;
        }
        
        double waitRatio = avgHold > 0 ? avgWait / avgHold : 0;
        double frequencyScore = Math.min(count / 100.0, 1.0);
        
        return (waitRatio * 0.7 + frequencyScore * 0.3) * 100;
    }

    public void reset() {
        acquireCount.reset();
        totalWaitTimeMs.reset();
        totalHoldTimeMs.reset();
        maxWaitTimeMs.set(0);
        maxHoldTimeMs.set(0);
        totalWaiters.reset();
    }
}
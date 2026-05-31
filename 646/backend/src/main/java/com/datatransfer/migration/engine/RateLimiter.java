package com.datatransfer.migration.engine;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

@Slf4j
public class RateLimiter {
    private final int maxRecordsPerSecond;
    private final Semaphore semaphore;
    private volatile long lastRefillTime;
    private volatile int availablePermits;

    public RateLimiter(int maxRecordsPerSecond) {
        if (maxRecordsPerSecond <= 0) {
            this.maxRecordsPerSecond = Integer.MAX_VALUE;
            this.semaphore = null;
            this.availablePermits = Integer.MAX_VALUE;
        } else {
            this.maxRecordsPerSecond = maxRecordsPerSecond;
            this.semaphore = new Semaphore(maxRecordsPerSecond);
            this.availablePermits = maxRecordsPerSecond;
        }
        this.lastRefillTime = System.currentTimeMillis();
    }

    public static RateLimiter unlimited() {
        return new RateLimiter(0);
    }

    public void acquire(int permits) throws InterruptedException {
        if (semaphore == null) return;
        refillPermits();
        semaphore.acquire(permits);
    }

    public boolean tryAcquire(int permits, long timeoutMs) throws InterruptedException {
        if (semaphore == null) return true;
        refillPermits();
        return semaphore.tryAcquire(permits, timeoutMs, TimeUnit.MILLISECONDS);
    }

    private void refillPermits() {
        long now = System.currentTimeMillis();
        long elapsed = now - lastRefillTime;
        if (elapsed >= 1000) {
            int released = maxRecordsPerSecond - semaphore.availablePermits();
            if (released > 0) {
                semaphore.release(released);
            }
            lastRefillTime = now;
        }
    }

    public void throttleBatch(int batchSize) {
        if (semaphore == null) return;
        try {
            int remaining = batchSize;
            while (remaining > 0) {
                int chunk = Math.min(remaining, maxRecordsPerSecond);
                acquire(chunk);
                remaining -= chunk;
                if (remaining > 0) {
                    long sleepMs = Math.max(100, 1000L * chunk / maxRecordsPerSecond);
                    Thread.sleep(sleepMs);
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Rate limiter interrupted");
        }
    }

    public int getMaxRecordsPerSecond() {
        return maxRecordsPerSecond;
    }

    public boolean isUnlimited() {
        return semaphore == null;
    }
}

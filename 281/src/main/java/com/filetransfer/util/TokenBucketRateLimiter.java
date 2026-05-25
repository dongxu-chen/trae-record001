package com.filetransfer.util;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class TokenBucketRateLimiter {
    private final long capacity;
    private final long refillRate;
    private final AtomicLong availableTokens;
    private final ScheduledExecutorService scheduler;
    private volatile boolean isRunning;
    private final Object lock = new Object();

    public TokenBucketRateLimiter(long maxBytesPerSecond) {
        this.capacity = maxBytesPerSecond;
        this.refillRate = maxBytesPerSecond / 10;
        this.availableTokens = new AtomicLong(maxBytesPerSecond);
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "token-bucket-refiller");
            t.setDaemon(true);
            return t;
        });
        this.isRunning = true;
        startRefillTask();
    }

    private void startRefillTask() {
        scheduler.scheduleAtFixedRate(() -> {
            if (!isRunning) {
                return;
            }
            try {
                long currentTokens = availableTokens.get();
                long newTokens = Math.min(capacity, currentTokens + refillRate);
                availableTokens.set(newTokens);
                synchronized (lock) {
                    lock.notifyAll();
                }
            } catch (Exception e) {
                log.error("令牌桶补充失败", e);
            }
        }, 100, 100, TimeUnit.MILLISECONDS);
    }

    public boolean tryAcquire(int bytes) {
        if (bytes <= 0) {
            return true;
        }
        long current = availableTokens.get();
        if (current >= bytes) {
            return availableTokens.compareAndSet(current, current - bytes);
        }
        return false;
    }

    public void acquire(int bytes) throws InterruptedException {
        if (bytes <= 0) {
            return;
        }
        if (bytes > capacity) {
            bytes = (int) capacity;
        }

        while (true) {
            if (tryAcquire(bytes)) {
                return;
            }
            synchronized (lock) {
                if (availableTokens.get() < bytes) {
                    lock.wait(10);
                }
            }
        }
    }

    public long getAvailableTokens() {
        return availableTokens.get();
    }

    public void stop() {
        isRunning = false;
        scheduler.shutdown();
        try {
            if (!scheduler.awaitTermination(1, TimeUnit.SECONDS)) {
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            scheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    public static TokenBucketRateLimiter create(long maxBytesPerSecond) {
        if (maxBytesPerSecond <= 0) {
            return new NoopRateLimiter();
        }
        return new TokenBucketRateLimiter(maxBytesPerSecond);
    }

    private static class NoopRateLimiter extends TokenBucketRateLimiter {
        public NoopRateLimiter() {
            super(Long.MAX_VALUE);
        }

        @Override
        public boolean tryAcquire(int bytes) {
            return true;
        }

        @Override
        public void acquire(int bytes) {
        }

        @Override
        public void stop() {
        }
    }
}

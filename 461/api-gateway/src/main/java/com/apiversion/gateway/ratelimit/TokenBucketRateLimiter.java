package com.apiversion.gateway.ratelimit;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

@Slf4j
public class TokenBucketRateLimiter {

    private final long maxRequestsPerSecond;
    private final long burstCapacity;
    private final long warmUpPeriodNanos;
    private final long startTimeNanos;

    private final AtomicLong availableTokens;
    private final AtomicLong lastRefillTimeNanos;
    private final LongAdder totalRequests = new LongAdder();
    private final LongAdder rejectedRequests = new LongAdder();

    public TokenBucketRateLimiter(long maxRequestsPerSecond, long burstCapacity, long warmUpPeriodSec) {
        this.maxRequestsPerSecond = maxRequestsPerSecond;
        this.burstCapacity = burstCapacity;
        this.warmUpPeriodNanos = warmUpPeriodSec * 1_000_000_000L;
        this.startTimeNanos = System.nanoTime();
        this.availableTokens = new AtomicLong(burstCapacity);
        this.lastRefillTimeNanos = new AtomicLong(System.nanoTime());
    }

    public boolean tryAcquire() {
        totalRequests.increment();

        long now = System.nanoTime();
        refillTokens(now);

        long currentTokens = availableTokens.get();
        if (currentTokens <= 0) {
            rejectedRequests.increment();
            return false;
        }

        if (availableTokens.compareAndSet(currentTokens, currentTokens - 1)) {
            return true;
        }

        rejectedRequests.increment();
        return false;
    }

    private void refillTokens(long now) {
        long lastRefill = lastRefillTimeNanos.get();
        long elapsedNanos = now - lastRefill;

        if (elapsedNanos <= 0) {
            return;
        }

        double currentRate = calculateWarmUpRate(now);
        long tokensToAdd = (long) (elapsedNanos * currentRate / 1_000_000_000.0);

        if (tokensToAdd > 0) {
            if (lastRefillTimeNanos.compareAndSet(lastRefill, now)) {
                availableTokens.updateAndGet(current ->
                        Math.min(burstCapacity, current + tokensToAdd));
            }
        }
    }

    private double calculateWarmUpRate(long now) {
        long elapsedSinceStart = now - startTimeNanos;
        if (elapsedSinceStart >= warmUpPeriodNanos) {
            return maxRequestsPerSecond;
        }

        double progress = (double) elapsedSinceStart / warmUpPeriodNanos;
        double warmUpFactor = 0.3 + 0.7 * progress;
        return maxRequestsPerSecond * warmUpFactor;
    }

    public double getCurrentRate() {
        return calculateWarmUpRate(System.nanoTime());
    }

    public long getAvailableTokens() {
        return availableTokens.get();
    }

    public long getTotalRequests() {
        return totalRequests.sum();
    }

    public long getRejectedRequests() {
        return rejectedRequests.sum();
    }

    public double getRejectionRate() {
        long total = totalRequests.sum();
        if (total == 0) {
            return 0.0;
        }
        return (double) rejectedRequests.sum() / total;
    }

    public void reset() {
        availableTokens.set(burstCapacity);
        lastRefillTimeNanos.set(System.nanoTime());
        totalRequests.reset();
        rejectedRequests.reset();
    }
}

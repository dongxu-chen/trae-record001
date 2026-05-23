package com.log.collector.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

public class BackpressureManager {

    private static final Logger logger = LoggerFactory.getLogger(BackpressureManager.class);

    private static volatile BackpressureManager instance;

    private final AtomicBoolean backpressureActive = new AtomicBoolean(false);
    private final AtomicLong backpressureStartTime = new AtomicLong(0);
    private final AtomicLong backpressureTriggerCount = new AtomicLong(0);
    private final AtomicLong backpressureReleaseCount = new AtomicLong(0);

    private volatile double highWatermark;
    private volatile double lowWatermark;
    private volatile long minBackpressureDurationMs;
    private volatile long maxBackpressureDurationMs;

    private BackpressureManager() {
        this.highWatermark = 0.85;
        this.lowWatermark = 0.50;
        this.minBackpressureDurationMs = 1000;
        this.maxBackpressureDurationMs = 30000;
    }

    public static BackpressureManager getInstance() {
        if (instance == null) {
            synchronized (BackpressureManager.class) {
                if (instance == null) {
                    instance = new BackpressureManager();
                }
            }
        }
        return instance;
    }

    public void configure(double highWatermark, double lowWatermark,
                          long minBackpressureMs, long maxBackpressureMs) {
        this.highWatermark = highWatermark;
        this.lowWatermark = lowWatermark;
        this.minBackpressureDurationMs = minBackpressureMs;
        this.maxBackpressureDurationMs = maxBackpressureMs;

        logger.info("BackpressureManager configured - high: {}, low: {}, minMs: {}, maxMs: {}",
                highWatermark, lowWatermark, minBackpressureMs, maxBackpressureMs);
    }

    public boolean shouldTriggerBackpressure(double channelUsage) {
        if (channelUsage >= highWatermark) {
            if (!backpressureActive.get()) {
                triggerBackpressure();
            }
            return true;
        }
        return false;
    }

    public boolean shouldReleaseBackpressure(double channelUsage) {
        if (backpressureActive.get() && channelUsage <= lowWatermark) {
            long elapsed = System.currentTimeMillis() - backpressureStartTime.get();
            if (elapsed >= minBackpressureDurationMs) {
                releaseBackpressure();
                return true;
            }
        }
        return false;
    }

    public void triggerBackpressure() {
        if (backpressureActive.compareAndSet(false, true)) {
            backpressureStartTime.set(System.currentTimeMillis());
            backpressureTriggerCount.incrementAndGet();
            logger.warn("=== BACKPRESSURE TRIGGERED === 暂停消费");
        }
    }

    public void releaseBackpressure() {
        if (backpressureActive.compareAndSet(true, false)) {
            backpressureReleaseCount.incrementAndGet();
            long duration = System.currentTimeMillis() - backpressureStartTime.get();
            logger.info("=== BACKPRESSURE RELEASED === 恢复消费, 持续时间: {}ms", duration);
        }
    }

    public boolean isBackpressureActive() {
        return backpressureActive.get();
    }

    public long getBackpressureDuration() {
        if (!backpressureActive.get()) {
            return 0;
        }
        return System.currentTimeMillis() - backpressureStartTime.get();
    }

    public boolean shouldPause() {
        if (!backpressureActive.get()) {
            return false;
        }
        long duration = getBackpressureDuration();
        return duration < maxBackpressureDurationMs;
    }

    public long getRecommendedPauseTime() {
        if (!backpressureActive.get()) {
            return 0;
        }
        long elapsed = getBackpressureDuration();
        long remaining = maxBackpressureDurationMs - elapsed;
        return Math.max(minBackpressureDurationMs, Math.min(remaining, 5000));
    }

    public double getHighWatermark() {
        return highWatermark;
    }

    public double getLowWatermark() {
        return lowWatermark;
    }

    public long getBackpressureTriggerCount() {
        return backpressureTriggerCount.get();
    }

    public long getBackpressureReleaseCount() {
        return backpressureReleaseCount.get();
    }

    public void reset() {
        backpressureActive.set(false);
        backpressureStartTime.set(0);
    }
}

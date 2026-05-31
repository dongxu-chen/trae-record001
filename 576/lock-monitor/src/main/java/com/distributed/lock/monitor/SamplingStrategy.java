package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class SamplingStrategy {

    private static final double DEFAULT_SAMPLE_RATE = 1.0;
    private static final double MIN_SAMPLE_RATE = 0.01;
    private static final long HIGH_FREQUENCY_THRESHOLD = 1000;
    private static final long ADJUSTMENT_WINDOW_MS = 60000;

    private final ConcurrentHashMap<String, LockFrequency> lockFrequencies = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AtomicLong> eventCounters = new ConcurrentHashMap<>();
    private volatile double globalSampleRate = DEFAULT_SAMPLE_RATE;
    private volatile long lastAdjustmentTime = System.currentTimeMillis();

    public boolean shouldSample(LockEvent event) {
        String lockKey = event.getLockKey();
        LockEvent.EventType eventType = event.getEventType();

        LockFrequency frequency = lockFrequencies.computeIfAbsent(lockKey, k -> new LockFrequency());
        frequency.recordEvent(eventType);

        long eventCount = eventCounters.computeIfAbsent(lockKey, k -> new AtomicLong(0)).incrementAndGet();

        double lockSampleRate = calculateLockSampleRate(frequency);

        double effectiveSampleRate = Math.min(lockSampleRate, globalSampleRate);

        long sampleInterval = (long) (1.0 / effectiveSampleRate);
        return eventCount % sampleInterval == 0;
    }

    private double calculateLockSampleRate(LockFrequency frequency) {
        long eventsPerMinute = frequency.getEventsPerMinute();

        if (eventsPerMinute > HIGH_FREQUENCY_THRESHOLD * 10) {
            return MIN_SAMPLE_RATE;
        } else if (eventsPerMinute > HIGH_FREQUENCY_THRESHOLD) {
            return 0.1;
        } else if (eventsPerMinute > HIGH_FREQUENCY_THRESHOLD / 2) {
            return 0.5;
        }
        return DEFAULT_SAMPLE_RATE;
    }

    public void adjustGlobalSampleRate(long totalEventsPerMinute) {
        long now = System.currentTimeMillis();
        if (now - lastAdjustmentTime < ADJUSTMENT_WINDOW_MS) {
            return;
        }
        lastAdjustmentTime = now;

        if (totalEventsPerMinute > 100000) {
            globalSampleRate = 0.1;
        } else if (totalEventsPerMinute > 50000) {
            globalSampleRate = 0.3;
        } else if (totalEventsPerMinute > 10000) {
            globalSampleRate = 0.5;
        } else {
            globalSampleRate = DEFAULT_SAMPLE_RATE;
        }
    }

    public double getGlobalSampleRate() {
        return globalSampleRate;
    }

    public double getLockSampleRate(String lockKey) {
        LockFrequency frequency = lockFrequencies.get(lockKey);
        if (frequency == null) {
            return DEFAULT_SAMPLE_RATE;
        }
        return calculateLockSampleRate(frequency);
    }

    public void cleanupOldData(long maxAgeMs) {
        long cutoffTime = System.currentTimeMillis() - maxAgeMs;
        lockFrequencies.entrySet().removeIf(entry -> entry.getValue().getLastEventTime() < cutoffTime);
    }

    private static class LockFrequency {
        private final AtomicLong totalEvents = new AtomicLong(0);
        private final AtomicLong windowStart = new AtomicLong(System.currentTimeMillis());
        private volatile long lastEventTime = System.currentTimeMillis();

        public void recordEvent(LockEvent.EventType eventType) {
            totalEvents.incrementAndGet();
            lastEventTime = System.currentTimeMillis();
        }

        public long getEventsPerMinute() {
            long now = System.currentTimeMillis();
            long elapsedMs = now - windowStart.get();

            if (elapsedMs > 60000) {
                windowStart.set(now);
                totalEvents.set(0);
                return 0;
            }

            if (elapsedMs == 0) {
                return totalEvents.get();
            }

            return (totalEvents.get() * 60000) / elapsedMs;
        }

        public long getLastEventTime() {
            return lastEventTime;
        }
    }
}
package com.distributed.lock.server.metrics;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class LockContentionAnalyzer {
    
    private static final Logger logger = LoggerFactory.getLogger(LockContentionAnalyzer.class);
    
    private final ConcurrentHashMap<String, LockMetrics> metricsRegistry;
    private final ConcurrentHashMap<String, Long> lockAcquireStartTimes;
    private final double highContentionThreshold;
    private final List<ContentionListener> listeners;

    public LockContentionAnalyzer() {
        this(50.0);
    }

    public LockContentionAnalyzer(double highContentionThreshold) {
        this.metricsRegistry = new ConcurrentHashMap<>();
        this.lockAcquireStartTimes = new ConcurrentHashMap<>();
        this.highContentionThreshold = highContentionThreshold;
        this.listeners = new ArrayList<>();
    }

    public void addContentionListener(ContentionListener listener) {
        listeners.add(listener);
    }

    public void recordLockAttempt(String lockName, String clientId) {
        String key = lockName + ":" + clientId;
        lockAcquireStartTimes.put(key, System.currentTimeMillis());
    }

    public void recordLockAcquired(String lockName, String clientId) {
        String key = lockName + ":" + clientId;
        Long startTime = lockAcquireStartTimes.remove(key);
        if (startTime != null) {
            long waitTime = System.currentTimeMillis() - startTime;
            LockMetrics metrics = getOrCreateMetrics(lockName);
            metrics.recordWaitTime(waitTime);
            metrics.recordAcquire();
            
            checkHighContention(lockName, metrics);
        }
    }

    public void recordLockReleased(String lockName, long holdTimeMs) {
        LockMetrics metrics = getOrCreateMetrics(lockName);
        metrics.recordHoldTime(holdTimeMs);
    }

    private void checkHighContention(String lockName, LockMetrics metrics) {
        if (metrics.getContentionScore() > highContentionThreshold) {
            ContentionEvent event = new ContentionEvent(
                    lockName,
                    metrics.getContentionScore(),
                    metrics.getAvgWaitTimeMs(),
                    metrics.getAvgHoldTimeMs(),
                    metrics.getAcquireCount()
            );
            
            for (ContentionListener listener : listeners) {
                try {
                    listener.onHighContention(event);
                } catch (Exception e) {
                    logger.error("Error in contention listener", e);
                }
            }
        }
    }

    private LockMetrics getOrCreateMetrics(String lockName) {
        return metricsRegistry.computeIfAbsent(lockName, LockMetrics::new);
    }

    public LockMetrics getLockMetrics(String lockName) {
        return metricsRegistry.get(lockName);
    }

    public List<LockMetrics> getHotLocks(int topN) {
        return metricsRegistry.values().stream()
                .sorted(Comparator.comparingDouble(LockMetrics::getContentionScore).reversed())
                .limit(topN)
                .collect(Collectors.toList());
    }

    public Collection<LockMetrics> getAllLockMetrics() {
        return metricsRegistry.values();
    }

    public double getOverallAvgWaitTimeMs() {
        if (metricsRegistry.isEmpty()) {
            return 0.0;
        }
        return metricsRegistry.values().stream()
                .mapToDouble(LockMetrics::getAvgWaitTimeMs)
                .average()
                .orElse(0.0);
    }

    public double getOverallAvgHoldTimeMs() {
        if (metricsRegistry.isEmpty()) {
            return 0.0;
        }
        return metricsRegistry.values().stream()
                .mapToDouble(LockMetrics::getAvgHoldTimeMs)
                .average()
                .orElse(0.0);
    }

    public void resetMetrics(String lockName) {
        LockMetrics metrics = metricsRegistry.get(lockName);
        if (metrics != null) {
            metrics.reset();
        }
    }

    public void resetAllMetrics() {
        for (LockMetrics metrics : metricsRegistry.values()) {
            metrics.reset();
        }
    }

    public interface ContentionListener {
        void onHighContention(ContentionEvent event);
    }

    public static class ContentionEvent {
        private final String lockName;
        private final double contentionScore;
        private final double avgWaitTimeMs;
        private final double avgHoldTimeMs;
        private final long acquireCount;
        private final long timestamp;

        public ContentionEvent(String lockName, double contentionScore, 
                               double avgWaitTimeMs, double avgHoldTimeMs, long acquireCount) {
            this.lockName = lockName;
            this.contentionScore = contentionScore;
            this.avgWaitTimeMs = avgWaitTimeMs;
            this.avgHoldTimeMs = avgHoldTimeMs;
            this.acquireCount = acquireCount;
            this.timestamp = System.currentTimeMillis();
        }

        public String getLockName() {
            return lockName;
        }

        public double getContentionScore() {
            return contentionScore;
        }

        public double getAvgWaitTimeMs() {
            return avgWaitTimeMs;
        }

        public double getAvgHoldTimeMs() {
            return avgHoldTimeMs;
        }

        public long getAcquireCount() {
            return acquireCount;
        }

        public long getTimestamp() {
            return timestamp;
        }

        @Override
        public String toString() {
            return String.format("ContentionEvent{lock='%s', score=%.2f, avgWait=%.2fms, avgHold=%.2fms, count=%d}",
                    lockName, contentionScore, avgWaitTimeMs, avgHoldTimeMs, acquireCount);
        }
    }
}
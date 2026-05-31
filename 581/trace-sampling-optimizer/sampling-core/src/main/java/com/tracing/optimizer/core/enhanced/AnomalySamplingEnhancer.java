package com.tracing.optimizer.core.enhanced;

import java.time.Instant;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

public class AnomalySamplingEnhancer {

    private final Map<String, TraceAnomalyContext> anomalyContextMap;
    private final Set<String> forceSampledTraceIds;
    private final long anomalyContextTtlMs;
    private final double errorRateThreshold;
    private final int minErrorCountForBoost;
    private final AtomicLong totalTracesProcessed;
    private final AtomicLong anomalyTracesDetected;
    private final AtomicLong forceSampledTraces;

    public AnomalySamplingEnhancer() {
        this(60000, 0.05, 3);
    }

    public AnomalySamplingEnhancer(long anomalyContextTtlMs, double errorRateThreshold, int minErrorCountForBoost) {
        this.anomalyContextTtlMs = anomalyContextTtlMs;
        this.errorRateThreshold = errorRateThreshold;
        this.minErrorCountForBoost = minErrorCountForBoost;
        this.anomalyContextMap = new ConcurrentHashMap<>();
        this.forceSampledTraceIds = ConcurrentHashMap.newKeySet();
        this.totalTracesProcessed = new AtomicLong(0);
        this.anomalyTracesDetected = new AtomicLong(0);
        this.forceSampledTraces = new AtomicLong(0);
    }

    public boolean shouldForceSample(String traceId, String serviceName, boolean hasError, int statusCode) {
        totalTracesProcessed.incrementAndGet();

        if (hasError || isErrorStatusCode(statusCode)) {
            anomalyTracesDetected.incrementAndGet();
            updateAnomalyContext(serviceName, true);
            forceSampledTraceIds.add(traceId);
            forceSampledTraces.incrementAndGet();
            return true;
        }

        TraceAnomalyContext context = anomalyContextMap.get(serviceName);
        if (context != null && context.isAnomalyActive(errorRateThreshold, minErrorCountForBoost)) {
            if (context.getBoostedSamplingRate() >= Math.random()) {
                forceSampledTraces.incrementAndGet();
                return true;
            }
        }

        return false;
    }

    public void recordTraceResult(String serviceName, boolean hasError) {
        updateAnomalyContext(serviceName, hasError);
    }

    private void updateAnomalyContext(String serviceName, boolean hasError) {
        TraceAnomalyContext context = anomalyContextMap.computeIfAbsent(
            serviceName, k -> new TraceAnomalyContext(anomalyContextTtlMs)
        );
        context.recordTrace(hasError);
    }

    private boolean isErrorStatusCode(int statusCode) {
        return statusCode >= 400 && statusCode != 404;
    }

    public double getServiceErrorRate(String serviceName) {
        TraceAnomalyContext context = anomalyContextMap.get(serviceName);
        return context != null ? context.getErrorRate() : 0.0;
    }

    public double getBoostedSamplingRate(String serviceName) {
        TraceAnomalyContext context = anomalyContextMap.get(serviceName);
        if (context != null && context.isAnomalyActive(errorRateThreshold, minErrorCountForBoost)) {
            return context.getBoostedSamplingRate();
        }
        return -1.0;
    }

    public void cleanupExpiredContexts() {
        long now = Instant.now().toEpochMilli();
        anomalyContextMap.entrySet().removeIf(entry -> entry.getValue().isExpired(now));
    }

    public Map<String, Object> getEnhancementStats() {
        return Map.of(
            "totalTracesProcessed", totalTracesProcessed.get(),
            "anomalyTracesDetected", anomalyTracesDetected.get(),
            "forceSampledTraces", forceSampledTraces.get(),
            "activeAnomalyServices", (long) anomalyContextMap.size(),
            "forceSamplingRate", totalTracesProcessed.get() > 0 
                ? (double) forceSampledTraces.get() / totalTracesProcessed.get() 
                : 0.0
        );
    }

    public static class TraceAnomalyContext {
        private final AtomicInteger totalTraces;
        private final AtomicInteger errorTraces;
        private final long ttlMs;
        private volatile long lastUpdateTime;
        private volatile double boostedSamplingRate;

        public TraceAnomalyContext(long ttlMs) {
            this.ttlMs = ttlMs;
            this.totalTraces = new AtomicInteger(0);
            this.errorTraces = new AtomicInteger(0);
            this.lastUpdateTime = Instant.now().toEpochMilli();
            this.boostedSamplingRate = 1.0;
        }

        public void recordTrace(boolean hasError) {
            totalTraces.incrementAndGet();
            if (hasError) {
                errorTraces.incrementAndGet();
            }
            lastUpdateTime = Instant.now().toEpochMilli();
            updateBoostedRate();
        }

        private void updateBoostedRate() {
            double errorRate = getErrorRate();
            if (errorRate >= 0.2) {
                boostedSamplingRate = 1.0;
            } else if (errorRate >= 0.1) {
                boostedSamplingRate = 0.8;
            } else if (errorRate >= 0.05) {
                boostedSamplingRate = 0.5;
            } else {
                boostedSamplingRate = 0.2;
            }
        }

        public double getErrorRate() {
            int total = totalTraces.get();
            return total > 0 ? (double) errorTraces.get() / total : 0.0;
        }

        public boolean isAnomalyActive(double threshold, int minErrorCount) {
            return errorTraces.get() >= minErrorCount && getErrorRate() >= threshold;
        }

        public double getBoostedSamplingRate() {
            return boostedSamplingRate;
        }

        public boolean isExpired(long now) {
            return (now - lastUpdateTime) > ttlMs;
        }

        public int getTotalTraces() {
            return totalTraces.get();
        }

        public int getErrorTraces() {
            return errorTraces.get();
        }
    }
}

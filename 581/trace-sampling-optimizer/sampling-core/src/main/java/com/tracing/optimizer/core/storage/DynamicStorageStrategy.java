package com.tracing.optimizer.core.storage;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class DynamicStorageStrategy {

    private final Map<String, ServiceHeatMetrics> serviceHeatMetrics;
    private final Duration hotThreshold;
    private final Duration warmThreshold;
    private final double hotSamplingRate;
    private final double warmSamplingRate;
    private final double coldSamplingRate;
    private final long accessCountHotThreshold;

    public DynamicStorageStrategy() {
        this(
            Duration.ofMinutes(5),
            Duration.ofHours(1),
            0.9,
            0.5,
            0.05,
            100
        );
    }

    public DynamicStorageStrategy(Duration hotThreshold, Duration warmThreshold,
                                  double hotSamplingRate, double warmSamplingRate, double coldSamplingRate,
                                  long accessCountHotThreshold) {
        this.hotThreshold = hotThreshold;
        this.warmThreshold = warmThreshold;
        this.hotSamplingRate = hotSamplingRate;
        this.warmSamplingRate = warmSamplingRate;
        this.coldSamplingRate = coldSamplingRate;
        this.accessCountHotThreshold = accessCountHotThreshold;
        this.serviceHeatMetrics = new ConcurrentHashMap<>();
    }

    public double getAdjustedSamplingRate(String serviceName, double baseRate) {
        ServiceHeatMetrics metrics = serviceHeatMetrics.computeIfAbsent(
            serviceName, k -> new ServiceHeatMetrics()
        );

        HeatTier tier = determineHeatTier(metrics);
        double tierMultiplier = getTierMultiplier(tier);

        return Math.min(1.0, Math.max(0.01, baseRate * tierMultiplier));
    }

    public HeatTier determineHeatTier(String serviceName) {
        ServiceHeatMetrics metrics = serviceHeatMetrics.get(serviceName);
        if (metrics == null) return HeatTier.COLD;
        return determineHeatTier(metrics);
    }

    private HeatTier determineHeatTier(ServiceHeatMetrics metrics) {
        long timeSinceLastAccess = System.currentTimeMillis() - metrics.getLastAccessTime();
        long recentAccessCount = metrics.getRecentAccessCount();

        if (timeSinceLastAccess < hotThreshold.toMillis() 
            || recentAccessCount > accessCountHotThreshold) {
            return HeatTier.HOT;
        } else if (timeSinceLastAccess < warmThreshold.toMillis()) {
            return HeatTier.WARM;
        } else {
            return HeatTier.COLD;
        }
    }

    private double getTierMultiplier(HeatTier tier) {
        return switch (tier) {
            case HOT -> hotSamplingRate / 0.1;
            case WARM -> warmSamplingRate / 0.1;
            case COLD -> coldSamplingRate / 0.1;
        };
    }

    public void recordServiceAccess(String serviceName) {
        ServiceHeatMetrics metrics = serviceHeatMetrics.computeIfAbsent(
            serviceName, k -> new ServiceHeatMetrics()
        );
        metrics.recordAccess();
    }

    public void recordTraceAccess(String traceId, String serviceName) {
        recordServiceAccess(serviceName);
    }

    public Map<String, HeatTier> getAllHeatTiers() {
        Map<String, HeatTier> tiers = new ConcurrentHashMap<>();
        for (Map.Entry<String, ServiceHeatMetrics> entry : serviceHeatMetrics.entrySet()) {
            tiers.put(entry.getKey(), determineHeatTier(entry.getValue()));
        }
        return tiers;
    }

    public Map<String, Object> getHeatStats(String serviceName) {
        ServiceHeatMetrics metrics = serviceHeatMetrics.get(serviceName);
        if (metrics == null) {
            return Map.of(
                "heatTier", HeatTier.COLD.name(),
                "timeSinceLastAccessMs", -1L,
                "recentAccessCount", 0L,
                "adjustedSamplingRate", coldSamplingRate
            );
        }

        HeatTier tier = determineHeatTier(metrics);
        return Map.of(
            "heatTier", tier.name(),
            "timeSinceLastAccessMs", System.currentTimeMillis() - metrics.getLastAccessTime(),
            "recentAccessCount", metrics.getRecentAccessCount(),
            "totalAccessCount", metrics.getTotalAccessCount(),
            "adjustedSamplingRate", getTierRate(tier)
        );
    }

    public double getTierRate(HeatTier tier) {
        return switch (tier) {
            case HOT -> hotSamplingRate;
            case WARM -> warmSamplingRate;
            case COLD -> coldSamplingRate;
        };
    }

    public void cleanupIdleMetrics() {
        long idleCutoff = System.currentTimeMillis() - Duration.ofDays(7).toMillis();
        serviceHeatMetrics.entrySet().removeIf(
            e -> e.getValue().getLastAccessTime() < idleCutoff
        );
    }

    public enum HeatTier {
        HOT,
        WARM,
        COLD
    }

    public static class ServiceHeatMetrics {
        private volatile long lastAccessTime;
        private final AtomicLong recentAccessCount;
        private final AtomicLong totalAccessCount;
        private final AtomicLong windowStartTime;
        private final Duration windowDuration = Duration.ofMinutes(5);

        public ServiceHeatMetrics() {
            this.lastAccessTime = System.currentTimeMillis();
            this.recentAccessCount = new AtomicLong(0);
            this.totalAccessCount = new AtomicLong(0);
            this.windowStartTime = new AtomicLong(System.currentTimeMillis());
        }

        public void recordAccess() {
            long now = System.currentTimeMillis();
            lastAccessTime = now;
            totalAccessCount.incrementAndGet();

            if (now - windowStartTime.get() > windowDuration.toMillis()) {
                windowStartTime.set(now);
                recentAccessCount.set(0);
            }
            recentAccessCount.incrementAndGet();
        }

        public long getLastAccessTime() {
            return lastAccessTime;
        }

        public long getRecentAccessCount() {
            return recentAccessCount.get();
        }

        public long getTotalAccessCount() {
            return totalAccessCount.get();
        }
    }
}

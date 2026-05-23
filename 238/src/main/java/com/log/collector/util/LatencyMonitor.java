package com.log.collector.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

public class LatencyMonitor {

    private static final Logger logger = LoggerFactory.getLogger(LatencyMonitor.class);

    private static volatile LatencyMonitor instance;

    private final ConcurrentHashMap<String, LatencyBucket> latencyBuckets = new ConcurrentHashMap<>();
    private final LongAdder totalEvents = new LongAdder();
    private final LongAdder totalLatencyMs = new LongAdder();
    private final AtomicLong minLatencyMs = new AtomicLong(Long.MAX_VALUE);
    private final AtomicLong maxLatencyMs = new AtomicLong(0);
    private final AtomicLong p50LatencyMs = new AtomicLong(0);
    private final AtomicLong p95LatencyMs = new AtomicLong(0);
    private final AtomicLong p99LatencyMs = new AtomicLong(0);

    private final long[] bucketBoundaries = {10, 50, 100, 500, 1000, 5000, 10000, 30000, 60000};
    private final String[] bucketNames = {"<10ms", "10-50ms", "50-100ms", "100-500ms", "500ms-1s", "1-5s", "5-10s", "10-30s", "30-60s", ">60s"};

    private volatile long lastReportTime = System.currentTimeMillis();
    private final long reportIntervalMs;

    private LatencyMonitor(long reportIntervalMs) {
        this.reportIntervalMs = reportIntervalMs;
        for (String name : bucketNames) {
            latencyBuckets.put(name, new LatencyBucket());
        }
    }

    public static LatencyMonitor getInstance() {
        if (instance == null) {
            synchronized (LatencyMonitor.class) {
                if (instance == null) {
                    instance = new LatencyMonitor(60000);
                }
            }
        }
        return instance;
    }

    public void recordLatency(long produceTimestamp, long ingestTimestamp, String level) {
        long latencyMs = ingestTimestamp - produceTimestamp;

        if (latencyMs < 0) {
            latencyMs = 0;
        }

        String bucket = getBucket(latencyMs);
        LatencyBucket latencyBucket = latencyBuckets.get(bucket);
        if (latencyBucket != null) {
            latencyBucket.count.increment();
            if (level != null) {
                latencyBucket.levelCounts.merge(level, 1L, Long::sum);
            }
        }

        totalEvents.increment();
        totalLatencyMs.add(latencyMs);

        updateMinMax(latencyMs);

        if (shouldReport()) {
            reportStats();
        }
    }

    public void recordLatency(EventLatency event) {
        recordLatency(event.produceTimestamp, event.ingestTimestamp, event.level);
    }

    private String getBucket(long latencyMs) {
        for (int i = 0; i < bucketBoundaries.length; i++) {
            if (latencyMs < bucketBoundaries[i]) {
                return bucketNames[i];
            }
        }
        return bucketNames[bucketNames.length - 1];
    }

    private void updateMinMax(long latencyMs) {
        long currentMin = minLatencyMs.get();
        if (latencyMs < currentMin) {
            minLatencyMs.compareAndSet(currentMin, latencyMs);
        }

        long currentMax = maxLatencyMs.get();
        if (latencyMs > currentMax) {
            maxLatencyMs.set(latencyMs);
        }
    }

    private boolean shouldReport() {
        long now = System.currentTimeMillis();
        if (now - lastReportTime >= reportIntervalMs) {
            lastReportTime = now;
            return true;
        }
        return false;
    }

    public void reportStats() {
        long total = totalEvents.sum();
        if (total == 0) {
            return;
        }

        double avgLatency = (double) totalLatencyMs.sum() / total;

        StringBuilder sb = new StringBuilder();
        sb.append("\n=== 端到端延迟统计 ===\n");
        sb.append(String.format("总事件数: %d\n", total));
        sb.append(String.format("平均延迟: %.2f ms\n", avgLatency));
        sb.append(String.format("最小延迟: %d ms\n", minLatencyMs.get() == Long.MAX_VALUE ? 0 : minLatencyMs.get()));
        sb.append(String.format("最大延迟: %d ms\n", maxLatencyMs.get()));
        sb.append("\n延迟分布:\n");

        long cumulative = 0;
        for (String name : bucketNames) {
            LatencyBucket bucket = latencyBuckets.get(name);
            if (bucket != null && bucket.count.sum() > 0) {
                double percentage = (double) bucket.count.sum() / total * 100;
                cumulative += bucket.count.sum();
                double cumulativePct = (double) cumulative / total * 100;
                sb.append(String.format("  %s: %d (%.2f%%, 累计: %.2f%%)\n",
                        name, bucket.count.sum(), percentage, cumulativePct));

                if (!bucket.levelCounts.isEmpty()) {
                    sb.append("    按级别分布: ");
                    bucket.levelCounts.forEach((level, cnt) -> {
                        double levelPct = (double) cnt / bucket.count.sum() * 100;
                        sb.append(String.format("%s: %d(%.1f%%) ", level, cnt, levelPct));
                    });
                    sb.append("\n");
                }
            }
        }

        logger.info(sb.toString());
    }

    public double getAverageLatency() {
        long total = totalEvents.sum();
        if (total == 0) {
            return 0.0;
        }
        return (double) totalLatencyMs.sum() / total;
    }

    public long getMinLatency() {
        return minLatencyMs.get() == Long.MAX_VALUE ? 0 : minLatencyMs.get();
    }

    public long getMaxLatency() {
        return maxLatencyMs.get();
    }

    public long getTotalEvents() {
        return totalEvents.sum();
    }

    public void reset() {
        totalEvents.reset();
        totalLatencyMs.reset();
        minLatencyMs.set(Long.MAX_VALUE);
        maxLatencyMs.set(0);
        latencyBuckets.values().forEach(LatencyBucket::reset);
        lastReportTime = System.currentTimeMillis();
    }

    public static class EventLatency {
        public final long produceTimestamp;
        public final long ingestTimestamp;
        public final String level;
        public final String service;

        public EventLatency(long produceTimestamp, long ingestTimestamp, String level, String service) {
            this.produceTimestamp = produceTimestamp;
            this.ingestTimestamp = ingestTimestamp;
            this.level = level;
            this.service = service;
        }
    }

    private static class LatencyBucket {
        final LongAdder count = new LongAdder();
        final ConcurrentHashMap<String, Long> levelCounts = new ConcurrentHashMap<>();

        void reset() {
            count.reset();
            levelCounts.clear();
        }
    }
}

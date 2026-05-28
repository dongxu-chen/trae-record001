package com.datasync.monitor.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SyncMetrics implements Serializable {
    private static final long serialVersionUID = 1L;

    private String datacenterId;
    private String nodeId;

    @Builder.Default
    private final LongAdder totalSyncCount = new LongAdder();

    @Builder.Default
    private final LongAdder successCount = new LongAdder();

    @Builder.Default
    private final LongAdder failureCount = new LongAdder();

    @Builder.Default
    private final LongAdder conflictCount = new LongAdder();

    @Builder.Default
    private final LongAdder insertCount = new LongAdder();

    @Builder.Default
    private final LongAdder updateCount = new LongAdder();

    @Builder.Default
    private final LongAdder deleteCount = new LongAdder();

    @Builder.Default
    private final AtomicLong minLatencyMs = new AtomicLong(Long.MAX_VALUE);

    @Builder.Default
    private final AtomicLong maxLatencyMs = new AtomicLong(0);

    @Builder.Default
    private final AtomicLong avgLatencyMs = new AtomicLong(0);

    @Builder.Default
    private final AtomicLong lastSyncTime = new AtomicLong(0);

    @Builder.Default
    private final AtomicLong startTime = new AtomicLong(System.currentTimeMillis());

    private volatile String status;

    public void recordSync(boolean success, long latencyMs, String operationType) {
        totalSyncCount.increment();
        if (success) {
            successCount.increment();
        } else {
            failureCount.increment();
        }

        if ("INSERT".equalsIgnoreCase(operationType)) {
            insertCount.increment();
        } else if ("UPDATE".equalsIgnoreCase(operationType)) {
            updateCount.increment();
        } else if ("DELETE".equalsIgnoreCase(operationType)) {
            deleteCount.increment();
        }

        updateLatency(latencyMs);
        lastSyncTime.set(System.currentTimeMillis());
    }

    public void recordConflict() {
        conflictCount.increment();
    }

    private void updateLatency(long latencyMs) {
        while (true) {
            long currentMin = minLatencyMs.get();
            if (latencyMs < currentMin) {
                if (minLatencyMs.compareAndSet(currentMin, latencyMs)) {
                    break;
                }
            } else {
                break;
            }
        }

        while (true) {
            long currentMax = maxLatencyMs.get();
            if (latencyMs > currentMax) {
                if (maxLatencyMs.compareAndSet(currentMax, latencyMs)) {
                    break;
                }
            } else {
                break;
            }
        }

        long total = totalSyncCount.sum();
        if (total > 0) {
            long currentAvg = avgLatencyMs.get();
            long newAvg = (currentAvg * (total - 1) + latencyMs) / total;
            avgLatencyMs.set(newAvg);
        }
    }

    public void reset() {
        totalSyncCount.reset();
        successCount.reset();
        failureCount.reset();
        conflictCount.reset();
        insertCount.reset();
        updateCount.reset();
        deleteCount.reset();
        minLatencyMs.set(Long.MAX_VALUE);
        maxLatencyMs.set(0);
        avgLatencyMs.set(0);
    }
}

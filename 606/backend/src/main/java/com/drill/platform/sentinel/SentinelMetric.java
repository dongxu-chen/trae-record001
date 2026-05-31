package com.drill.platform.sentinel;

import lombok.Data;

@Data
public class SentinelMetric {

    private long passedCount;
    private long blockedCount;
    private long degradedCount;
    private long totalCount;

    public synchronized void incrementPassed() {
        passedCount++;
        totalCount++;
    }

    public synchronized void incrementBlocked() {
        blockedCount++;
        totalCount++;
    }

    public synchronized void incrementDegraded() {
        degradedCount++;
        totalCount++;
    }

    public synchronized double getBlockRate() {
        return totalCount > 0 ? blockedCount * 100.0 / totalCount : 0;
    }

    public synchronized double getPassRate() {
        return totalCount > 0 ? passedCount * 100.0 / totalCount : 0;
    }
}

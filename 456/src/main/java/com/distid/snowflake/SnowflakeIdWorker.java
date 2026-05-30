package com.distid.snowflake;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class SnowflakeIdWorker {
    private final long workerId;
    private final long datacenterId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    private static final long WORKER_ID_BITS = 5L;
    private static final long DATACENTER_ID_BITS = 5L;
    private static final long MAX_WORKER_ID = ~(-1L << WORKER_ID_BITS);
    private static final long MAX_DATACENTER_ID = ~(-1L << DATACENTER_ID_BITS);
    private static final long SEQUENCE_BITS = 12L;

    private static final long WORKER_ID_SHIFT = SEQUENCE_BITS;
    private static final long DATACENTER_ID_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS;
    private static final long TIMESTAMP_LEFT_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS + DATACENTER_ID_BITS;
    private static final long SEQUENCE_MASK = ~(-1L << SEQUENCE_BITS);

    private static final long TWEPOCH = 1609459200000L;

    private final long maxTolerateBackwardMs;
    private final long maxWaitBackwardMs;
    private final NtpTimeSynchronizer timeSynchronizer;

    private volatile long totalBackwardWaitTime = 0;
    private volatile int backwardEventCount = 0;

    public SnowflakeIdWorker(long workerId, long datacenterId, long maxTolerateBackwardMs) {
        this(workerId, datacenterId, maxTolerateBackwardMs, 5000, null);
    }

    public SnowflakeIdWorker(long workerId, long datacenterId, long maxTolerateBackwardMs,
                             long maxWaitBackwardMs, NtpTimeSynchronizer timeSynchronizer) {
        if (workerId > MAX_WORKER_ID || workerId < 0) {
            throw new IllegalArgumentException("worker Id can't be greater than " + MAX_WORKER_ID + " or less than 0");
        }
        if (datacenterId > MAX_DATACENTER_ID || datacenterId < 0) {
            throw new IllegalArgumentException("datacenter Id can't be greater than " + MAX_DATACENTER_ID + " or less than 0");
        }
        this.workerId = workerId;
        this.datacenterId = datacenterId;
        this.maxTolerateBackwardMs = maxTolerateBackwardMs;
        this.maxWaitBackwardMs = maxWaitBackwardMs;
        this.timeSynchronizer = timeSynchronizer;
    }

    public synchronized long nextId() {
        long timestamp = getCurrentTimestamp();

        if (timestamp < lastTimestamp) {
            long backwardMs = lastTimestamp - timestamp;
            backwardEventCount++;

            if (backwardMs <= maxTolerateBackwardMs) {
                timestamp = waitForClockCatchUp(timestamp, backwardMs);
            } else if (backwardMs <= maxWaitBackwardMs) {
                log.warn("Clock backward detected: {}ms, waiting for catch up (max wait: {}ms)", backwardMs, maxWaitBackwardMs);
                timestamp = waitForClockCatchUp(timestamp, maxWaitBackwardMs);
            }

            if (timestamp < lastTimestamp) {
                if (timeSynchronizer != null && !timeSynchronizer.isSynchronizedOk()) {
                    timeSynchronizer.syncNow();
                }
                throw new ClockBackwardException(lastTimestamp - timestamp);
            }
        }

        if (lastTimestamp == timestamp) {
            sequence = (sequence + 1) & SEQUENCE_MASK;
            if (sequence == 0) {
                timestamp = tilNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        return ((timestamp - TWEPOCH) << TIMESTAMP_LEFT_SHIFT)
                | (datacenterId << DATACENTER_ID_SHIFT)
                | (workerId << WORKER_ID_SHIFT)
                | sequence;
    }

    private long waitForClockCatchUp(long currentTimestamp, long maxWaitMs) {
        long startTime = System.currentTimeMillis();
        long waitUntil = startTime + maxWaitMs;
        long timestamp = currentTimestamp;

        while (timestamp < lastTimestamp && System.currentTimeMillis() < waitUntil) {
            try {
                Thread.sleep(1);
                timestamp = getCurrentTimestamp();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }

        totalBackwardWaitTime += (System.currentTimeMillis() - startTime);
        return timestamp;
    }

    private long tilNextMillis(long lastTimestamp) {
        long timestamp = getCurrentTimestamp();
        while (timestamp <= lastTimestamp) {
            timestamp = getCurrentTimestamp();
        }
        return timestamp;
    }

    private long getCurrentTimestamp() {
        if (timeSynchronizer != null) {
            return timeSynchronizer.currentTimeMillis();
        }
        return System.currentTimeMillis();
    }

    protected long timeGen() {
        return getCurrentTimestamp();
    }

    public long getWorkerId() {
        return workerId;
    }

    public long getDatacenterId() {
        return datacenterId;
    }

    public long getLastTimestamp() {
        return lastTimestamp;
    }

    public long getTotalBackwardWaitTime() {
        return totalBackwardWaitTime;
    }

    public int getBackwardEventCount() {
        return backwardEventCount;
    }
}

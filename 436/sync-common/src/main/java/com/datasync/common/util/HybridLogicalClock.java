package com.datasync.common.util;

import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class HybridLogicalClock {
    private static final long MAX_CLOCK_OFFSET_MS = 5000;

    private final AtomicLong hlcTimestamp = new AtomicLong(0);
    private final AtomicLong logicalClock = new AtomicLong(0);
    private final String nodeId;

    public HybridLogicalClock(String nodeId) {
        this.nodeId = nodeId;
        this.hlcTimestamp.set(System.currentTimeMillis());
    }

    public synchronized HlcTimestamp now() {
        long now = System.currentTimeMillis();
        long currentHlc = hlcTimestamp.get();

        long newHlc = Math.max(currentHlc, now);
        long newLogical;

        if (newHlc == currentHlc) {
            newLogical = logicalClock.incrementAndGet();
        } else {
            newLogical = 0;
            logicalClock.set(0);
        }

        hlcTimestamp.set(newHlc);
        logicalClock.set(newLogical);

        if (newHlc - now > MAX_CLOCK_OFFSET_MS) {
            log.warn("HLC timestamp offset exceeds maximum: offset={}ms, max={}ms", newHlc - now, MAX_CLOCK_OFFSET_MS);
        }

        return new HlcTimestamp(newHlc, newLogical, nodeId);
    }

    public synchronized HlcTimestamp receive(HlcTimestamp remoteTimestamp) {
        long now = System.currentTimeMillis();
        long currentHlc = hlcTimestamp.get();
        long currentLogical = logicalClock.get();

        long remoteHlc = remoteTimestamp.getPhysicalTime();
        long remoteLogical = remoteTimestamp.getLogicalTime();

        if (remoteHlc - now > MAX_CLOCK_OFFSET_MS) {
            log.warn("Received remote timestamp exceeds maximum offset: offset={}ms, max={}ms",
                    remoteHlc - now, MAX_CLOCK_OFFSET_MS);
        }

        long newHlc = Math.max(currentHlc, Math.max(remoteHlc, now));
        long newLogical;

        if (newHlc == currentHlc && newHlc == remoteHlc) {
            newLogical = Math.max(currentLogical, remoteLogical) + 1;
        } else if (newHlc == currentHlc) {
            newLogical = currentLogical + 1;
        } else if (newHlc == remoteHlc) {
            newLogical = remoteLogical + 1;
        } else {
            newLogical = 0;
        }

        hlcTimestamp.set(newHlc);
        logicalClock.set(newLogical);

        return new HlcTimestamp(newHlc, newLogical, nodeId);
    }

    public synchronized HlcTimestamp receive(long remotePhysicalTime, long remoteLogicalTime) {
        return receive(new HlcTimestamp(remotePhysicalTime, remoteLogicalTime, "remote"));
    }

    public long getCurrentHlcTimestamp() {
        return hlcTimestamp.get();
    }

    public long getCurrentLogicalClock() {
        return logicalClock.get();
    }

    public static int compare(HlcTimestamp t1, HlcTimestamp t2) {
        if (t1 == null && t2 == null) return 0;
        if (t1 == null) return -1;
        if (t2 == null) return 1;

        int physicalCompare = Long.compare(t1.getPhysicalTime(), t2.getPhysicalTime());
        if (physicalCompare != 0) {
            return physicalCompare;
        }
        return Long.compare(t1.getLogicalTime(), t2.getLogicalTime());
    }

    public static class HlcTimestamp {
        private final long physicalTime;
        private final long logicalTime;
        private final String nodeId;

        public HlcTimestamp(long physicalTime, long logicalTime, String nodeId) {
            this.physicalTime = physicalTime;
            this.logicalTime = logicalTime;
            this.nodeId = nodeId;
        }

        public long getPhysicalTime() {
            return physicalTime;
        }

        public long getLogicalTime() {
            return logicalTime;
        }

        public String getNodeId() {
            return nodeId;
        }

        public String toKey() {
            return physicalTime + "_" + logicalTime;
        }

        @Override
        public String toString() {
            return "HlcTimestamp{" +
                    "physicalTime=" + physicalTime +
                    ", logicalTime=" + logicalTime +
                    ", nodeId='" + nodeId + '\'' +
                    '}';
        }
    }
}

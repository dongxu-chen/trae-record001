package com.mqmonitor.common.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class EndToEndTimestampManager {
    private static final Logger logger = LoggerFactory.getLogger(EndToEndTimestampManager.class);

    private static final long TIMESTAMP_TIMEOUT_MS = TimeUnit.MINUTES.toMillis(5);
    private static final long CLOCK_OFFSET_UPDATE_INTERVAL_MS = TimeUnit.MINUTES.toMillis(1);

    private final ConcurrentHashMap<String, TimestampEntry> pendingTimestamps = new ConcurrentHashMap<>();
    private final AtomicLong clockOffsetNs = new AtomicLong(0);
    private volatile long lastOffsetUpdateMs = 0;

    private static class TimestampEntry {
        final long sendTimeNs;
        final long createTimeMs;

        TimestampEntry(long sendTimeNs, long createTimeMs) {
            this.sendTimeNs = sendTimeNs;
            this.createTimeMs = createTimeMs;
        }
    }

    public static class EndToEndTimestamps {
        private final long produceSendTimeNs;
        private final long produceAckTimeNs;
        private final long consumeReceiveTimeNs;
        private final long produceLatencyNs;
        private final long queueLatencyNs;
        private final long consumeLatencyNs;
        private final long endToEndLatencyNs;
        private final boolean useMonotonicClock;

        public EndToEndTimestamps(long produceSendTimeNs, long produceAckTimeNs,
                                  long consumeReceiveTimeNs, long clockOffsetNs) {
            this.produceSendTimeNs = produceSendTimeNs;
            this.produceAckTimeNs = produceAckTimeNs;
            this.consumeReceiveTimeNs = consumeReceiveTimeNs;
            this.useMonotonicClock = true;

            long adjustedConsumeTime = consumeReceiveTimeNs - clockOffsetNs;
            this.produceLatencyNs = Math.max(0, produceAckTimeNs - produceSendTimeNs);
            this.queueLatencyNs = Math.max(0, adjustedConsumeTime - produceAckTimeNs);
            this.consumeLatencyNs = 0;
            this.endToEndLatencyNs = Math.max(0, adjustedConsumeTime - produceSendTimeNs);
        }

        public long getProduceLatencyMs() {
            return TimeUnit.NANOSECONDS.toMillis(produceLatencyNs);
        }

        public long getQueueLatencyMs() {
            return TimeUnit.NANOSECONDS.toMillis(queueLatencyNs);
        }

        public long getConsumeLatencyMs() {
            return TimeUnit.NANOSECONDS.toMillis(consumeLatencyNs);
        }

        public long getEndToEndLatencyMs() {
            return TimeUnit.NANOSECONDS.toMillis(endToEndLatencyNs);
        }

        public boolean isUseMonotonicClock() {
            return useMonotonicClock;
        }
    }

    public long createSendTimestamp(String messageId) {
        long nowNs = System.nanoTime();
        pendingTimestamps.put(messageId, new TimestampEntry(nowNs, System.currentTimeMillis()));
        cleanupExpired();
        return nowNs;
    }

    public Long getSendTimestamp(String messageId) {
        TimestampEntry entry = pendingTimestamps.get(messageId);
        if (entry != null) {
            return entry.sendTimeNs;
        }
        return null;
    }

    public void removePendingTimestamp(String messageId) {
        pendingTimestamps.remove(messageId);
    }

    public EndToEndTimestamps calculateLatency(String messageId, long consumeReceiveTimeNs) {
        TimestampEntry entry = pendingTimestamps.remove(messageId);
        if (entry == null) {
            return null;
        }

        return new EndToEndTimestamps(
                entry.sendTimeNs,
                entry.sendTimeNs + 1000000,
                consumeReceiveTimeNs,
                clockOffsetNs.get()
        );
    }

    public EndToEndTimestamps calculateLatency(long produceSendTimeNs, long consumeReceiveTimeNs) {
        return new EndToEndTimestamps(
                produceSendTimeNs,
                produceSendTimeNs + 1000000,
                consumeReceiveTimeNs,
                clockOffsetNs.get()
        );
    }

    public void updateClockOffset(long remoteMonotonicNs, long remoteWallClockMs) {
        long now = System.currentTimeMillis();
        if (now - lastOffsetUpdateMs < CLOCK_OFFSET_UPDATE_INTERVAL_MS) {
            return;
        }

        long localMonotonicNs = System.nanoTime();
        long localWallClockNs = TimeUnit.MILLISECONDS.toNanos(remoteWallClockMs);
        long newOffset = localMonotonicNs - remoteMonotonicNs;

        long oldOffset = clockOffsetNs.get();
        long smoothedOffset = (long) (oldOffset * 0.8 + newOffset * 0.2);
        clockOffsetNs.set(smoothedOffset);
        lastOffsetUpdateMs = now;

        logger.debug("Updated clock offset: {}ns (was: {}ns)", smoothedOffset, oldOffset);
    }

    public long getClockOffsetNs() {
        return clockOffsetNs.get();
    }

    private void cleanupExpired() {
        long now = System.currentTimeMillis();
        pendingTimestamps.entrySet().removeIf(entry ->
                now - entry.getValue().createTimeMs > TIMESTAMP_TIMEOUT_MS
        );
    }

    public static String generateMessageId(String prefix) {
        return prefix + "-" + System.nanoTime() + "-" + ThreadLocalRandom.current().nextLong(1000000);
    }

    private static class ThreadLocalRandom {
        private static final java.util.concurrent.ThreadLocalRandom INSTANCE =
                java.util.concurrent.ThreadLocalRandom.current();

        static long nextLong(long bound) {
            return INSTANCE.nextLong(bound);
        }
    }
}

package com.benchmark.generator;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class SnowflakeIdGenerator implements IdGenerator {

    private final long twepoch = 1288834974657L;

    private final long workerIdBits = 5L;
    private final long datacenterIdBits = 5L;
    private final long maxWorkerId = ~(-1L << workerIdBits);
    private final long maxDatacenterId = ~(-1L << datacenterIdBits);
    private final long sequenceBits = 12L;

    private final long workerIdShift = sequenceBits;
    private final long datacenterIdShift = sequenceBits + workerIdBits;
    private final long timestampLeftShift = sequenceBits + workerIdBits + datacenterIdBits;
    private final long sequenceMask = ~(-1L << sequenceBits);

    private final long workerId;
    private final long datacenterId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;

    private final AtomicLong clockDriftCount = new AtomicLong(0);
    private final AtomicLong clockBackwardCount = new AtomicLong(0);
    private final AtomicLong forcedWaitCount = new AtomicLong(0);
    private final AtomicLong totalWaitTime = new AtomicLong(0);

    @Getter
    private final ClockSimulator clockSimulator;

    public SnowflakeIdGenerator(long workerId, long datacenterId) {
        this(workerId, datacenterId, ClockSimulator.Mode.NORMAL, 0, 0);
    }

    public SnowflakeIdGenerator(long workerId, long datacenterId,
                                ClockSimulator.Mode clockMode,
                                long clockOffsetMs,
                                double clockBackProbability) {
        if (workerId > maxWorkerId || workerId < 0) {
            throw new IllegalArgumentException(String.format("worker Id can't be greater than %d or less than 0", maxWorkerId));
        }
        if (datacenterId > maxDatacenterId || datacenterId < 0) {
            throw new IllegalArgumentException(String.format("datacenter Id can't be greater than %d or less than 0", maxDatacenterId));
        }
        this.workerId = workerId;
        this.datacenterId = datacenterId;
        this.clockSimulator = new ClockSimulator(clockMode, clockOffsetMs, clockBackProbability);
    }

    @Override
    public synchronized String nextId() {
        long timestamp = clockSimulator.currentTimeMillis();

        if (timestamp < lastTimestamp) {
            clockBackwardCount.incrementAndGet();
            long offset = lastTimestamp - timestamp;

            if (offset <= 5) {
                try {
                    forcedWaitCount.incrementAndGet();
                    totalWaitTime.addAndGet(offset);
                    wait(offset);
                    timestamp = clockSimulator.currentTimeMillis();
                    if (timestamp < lastTimestamp) {
                        throw new RuntimeException(String.format(
                            "Clock moved backwards. Refusing to generate id for %d milliseconds", offset));
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new RuntimeException("Interrupted while waiting for clock recovery", e);
                }
            } else {
                throw new RuntimeException(String.format(
                    "Clock moved backwards. Refusing to generate id for %d milliseconds", offset));
            }
        }

        if (lastTimestamp == timestamp) {
            sequence = (sequence + 1) & sequenceMask;
            if (sequence == 0) {
                timestamp = tilNextMillis(lastTimestamp);
            }
        } else {
            sequence = 0L;
        }

        if (timestamp > lastTimestamp + 1) {
            clockDriftCount.incrementAndGet();
        }

        lastTimestamp = timestamp;

        long id = ((timestamp - twepoch) << timestampLeftShift)
                | (datacenterId << datacenterIdShift)
                | (workerId << workerIdShift)
                | sequence;

        return String.valueOf(id);
    }

    private long tilNextMillis(long lastTimestamp) {
        long timestamp = clockSimulator.currentTimeMillis();
        long waitTime = 0;
        while (timestamp <= lastTimestamp) {
            try {
                waitTime++;
                Thread.sleep(0, 100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
            timestamp = clockSimulator.currentTimeMillis();
        }
        if (waitTime > 0) {
            forcedWaitCount.incrementAndGet();
            totalWaitTime.addAndGet(waitTime / 1000);
        }
        return timestamp;
    }

    public ClockStatistics getStatistics() {
        return new ClockStatistics(
            clockDriftCount.get(),
            clockBackwardCount.get(),
            forcedWaitCount.get(),
            totalWaitTime.get(),
            clockSimulator.getTotalDriftApplied(),
            clockSimulator.getTotalBackwardApplied(),
            clockSimulator.getMode()
        );
    }

    @lombok.Data
    @lombok.AllArgsConstructor
    public static class ClockStatistics {
        private long clockDriftCount;
        private long clockBackwardCount;
        private long forcedWaitCount;
        private long totalWaitTimeMs;
        private long totalDriftApplied;
        private long totalBackwardApplied;
        private ClockSimulator.Mode clockMode;
    }

    public static class ClockSimulator {

        public enum Mode {
            NORMAL,
            CLOCK_DRIFT,
            CLOCK_BACKWARD,
            MIXED
        }

        private final Mode mode;
        private final long clockOffsetMs;
        private final double clockBackProbability;
        private final Random random = new Random();

        private long driftAccumulator = 0;
        private long currentDrift = 0;
        private final AtomicLong totalDriftApplied = new AtomicLong(0);
        private final AtomicLong totalBackwardApplied = new AtomicLong(0);

        public ClockSimulator(Mode mode, long clockOffsetMs, double clockBackProbability) {
            this.mode = mode;
            this.clockOffsetMs = clockOffsetMs;
            this.clockBackProbability = clockBackProbability;
        }

        public long currentTimeMillis() {
            long realTime = System.currentTimeMillis();

            switch (mode) {
                case CLOCK_DRIFT:
                    return simulateClockDrift(realTime);
                case CLOCK_BACKWARD:
                    return simulateClockBackward(realTime);
                case MIXED:
                    return simulateMixed(realTime);
                case NORMAL:
                default:
                    return realTime;
            }
        }

        private long simulateClockDrift(long realTime) {
            driftAccumulator++;
            if (driftAccumulator % 1000 == 0) {
                currentDrift += clockOffsetMs;
                totalDriftApplied.addAndGet(clockOffsetMs);
            }
            return realTime + currentDrift;
        }

        private long simulateClockBackward(long realTime) {
            if (random.nextDouble() < clockBackProbability) {
                long backAmount = clockOffsetMs + random.nextInt((int) clockOffsetMs * 2);
                totalBackwardApplied.addAndGet(backAmount);
                return realTime - backAmount;
            }
            return realTime;
        }

        private long simulateMixed(long realTime) {
            double r = random.nextDouble();
            if (r < clockBackProbability / 2) {
                long backAmount = clockOffsetMs + random.nextInt((int) clockOffsetMs);
                totalBackwardApplied.addAndGet(backAmount);
                return realTime - backAmount;
            } else if (r < clockBackProbability) {
                driftAccumulator++;
                if (driftAccumulator % 500 == 0) {
                    long drift = clockOffsetMs / 2;
                    currentDrift += drift;
                    totalDriftApplied.addAndGet(drift);
                }
                return realTime + currentDrift;
            }
            return realTime + currentDrift;
        }

        public long getTotalDriftApplied() {
            return totalDriftApplied.get();
        }

        public long getTotalBackwardApplied() {
            return totalBackwardApplied.get();
        }

        public Mode getMode() {
            return mode;
        }
    }
}

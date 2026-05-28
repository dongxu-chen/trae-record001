package com.mqmonitor.common.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

public class LatencyDistribution {
    private static final Logger logger = LoggerFactory.getLogger(LatencyDistribution.class);

    private final int maxSamples;
    private final long windowMs;
    private final List<LatencySample> samples = new ArrayList<>();
    private final ReentrantLock lock = new ReentrantLock();

    public LatencyDistribution() {
        this(10000, TimeUnit.HOURS.toMillis(1));
    }

    public LatencyDistribution(int maxSamples, long windowMs) {
        this.maxSamples = maxSamples;
        this.windowMs = windowMs;
    }

    public void record(long latencyMs) {
        record(latencyMs, System.currentTimeMillis());
    }

    public void record(long latencyMs, long timestamp) {
        lock.lock();
        try {
            evictExpired(timestamp);

            if (samples.size() >= maxSamples) {
                samples.remove(0);
            }

            samples.add(new LatencySample(latencyMs, timestamp));
        } finally {
            lock.unlock();
        }
    }

    public long getP50() {
        return getPercentile(50.0);
    }

    public long getP95() {
        return getPercentile(95.0);
    }

    public long getP99() {
        return getPercentile(99.0);
    }

    public long getPercentile(double percentile) {
        lock.lock();
        try {
            if (samples.isEmpty()) {
                return 0;
            }

            evictExpired(System.currentTimeMillis());

            List<Long> latencies = new ArrayList<>();
            for (LatencySample sample : samples) {
                latencies.add(sample.latencyMs);
            }

            Collections.sort(latencies);

            if (latencies.size() == 1) {
                return latencies.get(0);
            }

            double index = (percentile / 100.0) * (latencies.size() - 1);
            int lower = (int) Math.floor(index);
            int upper = (int) Math.ceil(index);

            if (lower == upper) {
                return latencies.get(lower);
            }

            double weight = index - lower;
            return Math.round(latencies.get(lower) * (1 - weight) + latencies.get(upper) * weight);
        } finally {
            lock.unlock();
        }
    }

    public double getMean() {
        lock.lock();
        try {
            if (samples.isEmpty()) {
                return 0.0;
            }

            long sum = 0;
            for (LatencySample sample : samples) {
                sum += sample.latencyMs;
            }

            return (double) sum / samples.size();
        } finally {
            lock.unlock();
        }
    }

    public int getSampleCount() {
        lock.lock();
        try {
            evictExpired(System.currentTimeMillis());
            return samples.size();
        } finally {
            lock.unlock();
        }
    }

    private void evictExpired(long now) {
        long cutoff = now - windowMs;
        while (!samples.isEmpty() && samples.get(0).timestamp < cutoff) {
            samples.remove(0);
        }
    }

    public void clear() {
        lock.lock();
        try {
            samples.clear();
        } finally {
            lock.unlock();
        }
    }

    private static class LatencySample {
        final long latencyMs;
        final long timestamp;

        LatencySample(long latencyMs, long timestamp) {
            this.latencyMs = latencyMs;
            this.timestamp = timestamp;
        }
    }
}

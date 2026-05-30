package com.distid.metrics;

import com.tdunning.math.stats.TDigest;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Slf4j
public class TDigestPercentiles {

    private static final double COMPRESSION = 100.0;
    private static final int MAX_SAMPLES = 100000;
    private static final long ROTATION_INTERVAL_MS = 60000;

    private volatile TDigest currentDigest;
    private volatile TDigest previousDigest;
    private final ReadWriteLock digestLock = new ReentrantReadWriteLock();

    private final ConcurrentLinkedQueue<Double> buffer = new ConcurrentLinkedQueue<>();
    private final AtomicLong bufferCount = new AtomicLong(0);
    private volatile long lastRotationTime;

    private final String metricsPrefix;

    public TDigestPercentiles(MeterRegistry registry, String metricsPrefix) {
        this.metricsPrefix = metricsPrefix;
        this.currentDigest = TDigest.createDigest(COMPRESSION);
        this.previousDigest = TDigest.createDigest(COMPRESSION);
        this.lastRotationTime = System.currentTimeMillis();

        registerGauges(registry);
        startDigestRotation();
    }

    private void registerGauges(MeterRegistry registry) {
        double[] percentiles = {0.5, 0.75, 0.90, 0.95, 0.99, 0.999};
        String[] labels = {"p50", "p75", "p90", "p95", "p99", "p999"};

        for (int i = 0; i < percentiles.length; i++) {
            final double p = percentiles[i];
            final String label = labels[i];
            Gauge.builder(metricsPrefix + "_" + label, () -> getPercentile(p))
                    .description("T-Digest percentile " + label)
                    .register(registry);
        }
    }

    public void record(double value) {
        buffer.offer(value);
        long count = bufferCount.incrementAndGet();

        if (count > 1000) {
            flushBuffer();
        }
    }

    private void flushBuffer() {
        digestLock.writeLock().lock();
        try {
            Double value;
            int flushed = 0;
            while ((value = buffer.poll()) != null && flushed < MAX_SAMPLES) {
                currentDigest.add(value);
                flushed++;
            }
            bufferCount.addAndGet(-flushed);
        } finally {
            digestLock.writeLock().unlock();
        }
    }

    private void startDigestRotation() {
        Thread rotationThread = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(ROTATION_INTERVAL_MS);
                    rotateDigests();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Failed to rotate T-Digest", e);
                }
            }
        }, "tdigest-rotation");
        rotationThread.setDaemon(true);
        rotationThread.start();
    }

    private void rotateDigests() {
        long now = System.currentTimeMillis();
        if (now - lastRotationTime < ROTATION_INTERVAL_MS) {
            return;
        }

        flushBuffer();
        digestLock.writeLock().lock();
        try {
            previousDigest = currentDigest;
            currentDigest = TDigest.createDigest(COMPRESSION);
            lastRotationTime = now;
            log.debug("T-Digest rotated, previous size={}", previousDigest.size());
        } finally {
            digestLock.writeLock().unlock();
        }
    }

    public double getPercentile(double q) {
        flushBuffer();
        digestLock.readLock().lock();
        try {
            double currentSize = currentDigest.size();
            double previousSize = previousDigest.size();
            double totalSize = currentSize + previousSize;

            if (totalSize == 0) {
                return 0.0;
            }

            if (previousSize == 0) {
                return currentDigest.quantile(q);
            }

            if (currentSize == 0) {
                return previousDigest.quantile(q);
            }

            double weight = currentSize / totalSize;
            double currentValue = currentDigest.quantile(q);
            double previousValue = previousDigest.quantile(q);

            return currentValue * weight + previousValue * (1 - weight);
        } finally {
            digestLock.readLock().unlock();
        }
    }

    public long getCount() {
        digestLock.readLock().lock();
        try {
            return (long) (currentDigest.size() + previousDigest.size());
        } finally {
            digestLock.readLock().unlock();
        }
    }
}

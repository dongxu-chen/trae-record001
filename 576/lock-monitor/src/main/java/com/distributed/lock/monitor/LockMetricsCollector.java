package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class LockMetricsCollector {

    private final MeterRegistry meterRegistry;
    private final ConcurrentHashMap<String, Counter> acquireCounters = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Counter> failCounters = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Timer> acquireTimers = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, DistributionSummary> waitTimeSummaries = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AtomicLong> heldLocksGauge = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AtomicLong> contentionCounters = new ConcurrentHashMap<>();

    @Autowired
    public LockMetricsCollector(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    public void recordEvent(LockEvent event) {
        String lockKey = event.getLockKey();
        String lockType = event.getLockType();
        LockEvent.EventType eventType = event.getEventType();

        switch (eventType) {
            case ACQUIRE_SUCCESS:
                recordAcquireSuccess(lockKey, lockType, event.getWaitTimeMs());
                break;
            case ACQUIRE_FAIL:
                recordAcquireFail(lockKey, lockType);
                break;
            case RELEASE_SUCCESS:
                recordRelease(lockKey, lockType);
                break;
            default:
                break;
        }
    }

    private void recordAcquireSuccess(String lockKey, String lockType, Long waitTimeMs) {
        String counterKey = lockType + ":" + lockKey;

        Counter counter = acquireCounters.computeIfAbsent(counterKey, k -> Counter.builder("lock_acquire_total")
                .description("Total number of lock acquisitions")
                .tag("lockKey", lockKey)
                .tag("lockType", lockType)
                .tag("result", "success")
                .register(meterRegistry));
        counter.increment();

        if (waitTimeMs != null) {
            DistributionSummary summary = waitTimeSummaries.computeIfAbsent(counterKey, k -> DistributionSummary.builder("lock_wait_time_ms")
                    .description("Lock wait time in milliseconds")
                    .tag("lockKey", lockKey)
                    .tag("lockType", lockType)
                    .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                    .register(meterRegistry));
            summary.record(waitTimeMs);
        }

        AtomicLong heldCount = heldLocksGauge.computeIfAbsent(counterKey, k -> {
            AtomicLong atomicLong = new AtomicLong(0);
            Gauge.builder("lock_held_current", atomicLong, AtomicLong::get)
                    .description("Current number of held locks")
                    .tag("lockKey", lockKey)
                    .tag("lockType", lockType)
                    .register(meterRegistry);
            return atomicLong;
        });
        heldCount.incrementAndGet();
    }

    private void recordAcquireFail(String lockKey, String lockType) {
        String counterKey = lockType + ":" + lockKey;

        Counter counter = failCounters.computeIfAbsent(counterKey, k -> Counter.builder("lock_acquire_total")
                .description("Total number of lock acquisitions")
                .tag("lockKey", lockKey)
                .tag("lockType", lockType)
                .tag("result", "fail")
                .register(meterRegistry));
        counter.increment();

        AtomicLong contentionCount = contentionCounters.computeIfAbsent(counterKey, k -> {
            AtomicLong atomicLong = new AtomicLong(0);
            Gauge.builder("lock_contention_total", atomicLong, AtomicLong::get)
                    .description("Total lock contentions")
                    .tag("lockKey", lockKey)
                    .tag("lockType", lockType)
                    .register(meterRegistry);
            return atomicLong;
        });
        contentionCount.incrementAndGet();
    }

    private void recordRelease(String lockKey, String lockType) {
        String counterKey = lockType + ":" + lockKey;
        AtomicLong heldCount = heldLocksGauge.get(counterKey);
        if (heldCount != null) {
            heldCount.decrementAndGet();
        }
    }

    public void recordHoldTime(String lockKey, String lockType, long holdTimeMs) {
        String counterKey = lockType + ":" + lockKey;
        DistributionSummary summary = waitTimeSummaries.computeIfAbsent(counterKey, k -> DistributionSummary.builder("lock_hold_time_ms")
                .description("Lock hold time in milliseconds")
                .tag("lockKey", lockKey)
                .tag("lockType", lockType)
                .publishPercentiles(0.5, 0.75, 0.95, 0.99)
                .register(meterRegistry));
        summary.record(holdTimeMs);
    }
}
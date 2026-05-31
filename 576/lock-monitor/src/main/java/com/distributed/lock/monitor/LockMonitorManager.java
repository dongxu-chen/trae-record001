package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.core.LockEventListener;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class LockMonitorManager {

    private static final Logger logger = LoggerFactory.getLogger(LockMonitorManager.class);

    private final LockMetricsCollector metricsCollector;
    private final LockEventEsStorage esStorage;
    private final List<LockEventListener> listeners = new ArrayList<>();
    private final ConcurrentHashMap<String, Long> lockAcquireTimes = new ConcurrentHashMap<>();

    private AsyncEventProcessor asyncEventProcessor;
    private SamplingStrategy samplingStrategy;

    @Autowired
    public LockMonitorManager(LockMetricsCollector metricsCollector, LockEventEsStorage esStorage) {
        this.metricsCollector = metricsCollector;
        this.esStorage = esStorage;
    }

    @PostConstruct
    public void init() {
        samplingStrategy = new SamplingStrategy();

        addListener(metricsCollector::recordEvent);
        addListener(esStorage);

        asyncEventProcessor = new AsyncEventProcessor(listeners, samplingStrategy);
        asyncEventProcessor.start();

        logger.info("LockMonitorManager initialized with async sampling");
    }

    @PreDestroy
    public void shutdown() {
        if (asyncEventProcessor != null) {
            asyncEventProcessor.stop();
        }
    }

    public void addListener(LockEventListener listener) {
        if (listener != null) {
            listeners.add(listener);
        }
    }

    public void removeListener(LockEventListener listener) {
        listeners.remove(listener);
    }

    public void onLockEvent(LockEvent event) {
        if (event == null) {
            return;
        }

        trackHoldTime(event);

        if (asyncEventProcessor != null) {
            boolean submitted = asyncEventProcessor.submit(event);
            if (!submitted) {
                logger.debug("Event queue full, dropped event for lock: {}", event.getLockKey());
            }
        } else {
            for (LockEventListener listener : listeners) {
                try {
                    listener.onEvent(event);
                } catch (Exception e) {
                    logger.warn("Listener failed to process event", e);
                }
            }
        }
    }

    private void trackHoldTime(LockEvent event) {
        String lockKey = event.getLockKey();
        String ownerId = event.getOwnerId();
        String lockKeyWithOwner = lockKey + ":" + ownerId;

        if (event.getEventType() == LockEvent.EventType.ACQUIRE_SUCCESS) {
            lockAcquireTimes.put(lockKeyWithOwner, event.getTimestamp());
        } else if (event.getEventType() == LockEvent.EventType.RELEASE_SUCCESS) {
            Long acquireTime = lockAcquireTimes.remove(lockKeyWithOwner);
            if (acquireTime != null) {
                long holdTimeMs = event.getTimestamp() - acquireTime;
                metricsCollector.recordHoldTime(lockKey, event.getLockType(), holdTimeMs);
            }
        }
    }

    public AsyncEventProcessor getAsyncEventProcessor() {
        return asyncEventProcessor;
    }

    public SamplingStrategy getSamplingStrategy() {
        return samplingStrategy;
    }
}
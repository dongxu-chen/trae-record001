package com.datasync.conflict;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
public class ConflictEngine {
    private final ConflictResolutionStrategy strategy;
    private final Cache<String, DataChangeEvent> eventCache;
    private final ReentrantLock lock = new ReentrantLock();
    private final long conflictWindowMs;

    @Builder
    public ConflictEngine(String strategyName,
                          long cacheExpireMinutes,
                          long cacheMaxSize,
                          long conflictWindowMs) {
        this.strategy = createStrategy(strategyName);
        this.conflictWindowMs = conflictWindowMs > 0 ? conflictWindowMs : SyncConstants.DEFAULT_CONFLICT_WINDOW_MS;

        CacheBuilder<Object, Object> cacheBuilder = CacheBuilder.newBuilder()
                .expireAfterWrite(cacheExpireMinutes > 0 ? cacheExpireMinutes : 10, TimeUnit.MINUTES);

        if (cacheMaxSize > 0) {
            cacheBuilder.maximumSize(cacheMaxSize);
        }

        this.eventCache = cacheBuilder.build();
    }

    private ConflictResolutionStrategy createStrategy(String strategyName) {
        if (strategyName == null || strategyName.isEmpty() || "HLC_VERSION".equalsIgnoreCase(strategyName)) {
            return new HlcVersionStrategy();
        } else if ("TIMESTAMP_BASED".equalsIgnoreCase(strategyName)) {
            return new TimestampBasedStrategy();
        } else if ("BUSINESS_VERSION".equalsIgnoreCase(strategyName)) {
            return new BusinessVersionStrategy();
        }
        throw new IllegalArgumentException("Unknown conflict resolution strategy: " + strategyName);
    }

    public ConflictResult checkAndResolve(DataChangeEvent incomingEvent) {
        lock.lock();
        try {
            String uniqueKey = incomingEvent.getUniqueKey();

            if (incomingEvent.getBusinessKey() == null || incomingEvent.getBusinessKey().isEmpty()) {
                log.debug("No business key for event {}, skipping conflict detection", incomingEvent.getEventId());
                return ConflictResult.noConflict();
            }

            DataChangeEvent existingEvent = eventCache.getIfPresent(uniqueKey);

            if (existingEvent == null) {
                log.debug("No existing event found for key: {}, adding to cache", uniqueKey);
                eventCache.put(uniqueKey, incomingEvent);
                return ConflictResult.noConflict();
            }

            long hlcDiff = getHlcDifference(incomingEvent, existingEvent);
            if (hlcDiff > conflictWindowMs * 1000) {
                log.debug("Events outside conflict window (HLC): hlcDiff={}, window={}ms, updating cache", hlcDiff, conflictWindowMs);
                eventCache.put(uniqueKey, incomingEvent);
                return ConflictResult.noConflict();
            }

            log.info("Conflict detected for key: {}, incomingEventId={}, existingEventId={}",
                    uniqueKey, incomingEvent.getEventId(), existingEvent.getEventId());

            ConflictResult result = strategy.resolve(incomingEvent, existingEvent);

            if (result.isHasConflict() && result.getResolution() == ConflictResult.ConflictResolution.APPLY_NEWER) {
                if (result.getWinnerEventId() != null && result.getWinnerEventId().equals(incomingEvent.getEventId())) {
                    eventCache.put(uniqueKey, incomingEvent);
                }
            }

            return result;
        } finally {
            lock.unlock();
        }
    }

    private long getHlcDifference(DataChangeEvent e1, DataChangeEvent e2) {
        Long h1 = e1.getHlcTimestamp();
        Long h2 = e2.getHlcTimestamp();
        if (h1 == null || h2 == null) {
            return Long.MAX_VALUE;
        }
        return Math.abs(h1 - h2);
    }

    public void updateCache(DataChangeEvent event) {
        lock.lock();
        try {
            String uniqueKey = event.getUniqueKey();
            eventCache.put(uniqueKey, event);
            log.debug("Updated cache for key: {}, eventId: {}", uniqueKey, event.getEventId());
        } finally {
            lock.unlock();
        }
    }

    public void removeFromCache(DataChangeEvent event) {
        lock.lock();
        try {
            String uniqueKey = event.getUniqueKey();
            eventCache.invalidate(uniqueKey);
            log.debug("Removed from cache for key: {}, eventId: {}", uniqueKey, event.getEventId());
        } finally {
            lock.unlock();
        }
    }

    private long getEventTimestamp(DataChangeEvent event) {
        if (event.getExecutionTime() != null && event.getExecutionTime() > 0) {
            return event.getExecutionTime();
        }
        if (event.getTimestamp() != null) {
            return event.getTimestamp();
        }
        return 0L;
    }

    public String getStrategyName() {
        return strategy.getStrategyName();
    }

    public long getCacheSize() {
        return eventCache.size();
    }

    public void cleanCache() {
        lock.lock();
        try {
            eventCache.cleanUp();
            log.info("Cache cleaned, current size: {}", eventCache.size());
        } finally {
            lock.unlock();
        }
    }
}

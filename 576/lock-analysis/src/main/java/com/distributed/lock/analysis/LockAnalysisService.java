package com.distributed.lock.analysis;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.monitor.LockEventEsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

@Service
public class LockAnalysisService {

    private static final Logger logger = LoggerFactory.getLogger(LockAnalysisService.class);

    private final LockEventEsRepository esRepository;
    private final ConcurrentHashMap<String, LockStatistics> lockStatisticsMap = new ConcurrentHashMap<>();
    private final Set<String> dirtyLocks = ConcurrentHashMap.newKeySet();

    private final DynamicWindow dynamicWindow = new DynamicWindow();
    private final IncrementalDeadlockDetector deadlockDetector = new IncrementalDeadlockDetector();

    private ScheduledExecutorService scheduler;

    private volatile List<DeadlockInfo> cachedDeadlockResults = new ArrayList<>();
    private volatile long lastDeadlockAnalysisTime = 0;

    @Autowired
    public LockAnalysisService(LockEventEsRepository esRepository) {
        this.esRepository = esRepository;
    }

    @PostConstruct
    public void init() {
        scheduler = Executors.newScheduledThreadPool(2, r -> {
            Thread thread = new Thread(r, "lock-analysis-worker");
            thread.setDaemon(true);
            return thread;
        });

        scheduler.scheduleAtFixedRate(this::processDirtyLocks, 1, 1, TimeUnit.SECONDS);
        scheduler.scheduleAtFixedRate(this::adjustDynamicWindow, 5, 5, TimeUnit.SECONDS);

        logger.info("LockAnalysisService initialized with incremental analysis and dynamic window");
    }

    public void analyzeEvent(LockEvent event) {
        String lockKey = event.getLockKey();
        LockStatistics stats = lockStatisticsMap.computeIfAbsent(lockKey,
                k -> new LockStatistics(lockKey, event.getLockType()));

        boolean changed = false;
        switch (event.getEventType()) {
            case ACQUIRE_SUCCESS:
                stats.incrementAcquireCount();
                dynamicWindow.recordEvent(lockKey, event.getTimestamp());
                if (event.getWaitTimeMs() != null) {
                    stats.addWaitTime(event.getWaitTimeMs());
                }
                stats.recordAcquire(event.getOwnerId(), event.getThreadId(), event.getTimestamp());
                changed = true;
                break;
            case ACQUIRE_FAIL:
                stats.incrementFailCount();
                stats.incrementContentionCount();
                changed = true;
                break;
            case RELEASE_SUCCESS:
                if (event.getHoldTimeMs() != null) {
                    stats.addHoldTime(event.getHoldTimeMs());
                }
                stats.recordRelease(event.getOwnerId(), event.getTimestamp());
                changed = true;
                break;
            default:
                break;
        }

        if (changed) {
            dirtyLocks.add(lockKey);
        }
    }

    private void processDirtyLocks() {
        if (dirtyLocks.isEmpty()) {
            return;
        }

        Set<String> locksToProcess = new HashSet<>(dirtyLocks);
        dirtyLocks.removeAll(locksToProcess);

        for (String lockKey : locksToProcess) {
            LockStatistics stats = lockStatisticsMap.get(lockKey);
            if (stats != null) {
                deadlockDetector.updateLockState(lockKey, stats);
            }
        }

        if (!locksToProcess.isEmpty()) {
            cachedDeadlockResults = deadlockDetector.detectDeadlocksIncremental(locksToProcess);
            lastDeadlockAnalysisTime = System.currentTimeMillis();
            logger.debug("Processed {} dirty locks, found {} potential deadlocks",
                    locksToProcess.size(), cachedDeadlockResults.size());
        }
    }

    private void adjustDynamicWindow() {
        long totalEvents = dynamicWindow.getTotalEventsInLastMinute();
        dynamicWindow.adjustWindowSize(totalEvents);
        logger.debug("Dynamic window adjusted. Current window: {}ms, Events/min: {}",
                dynamicWindow.getCurrentWindowSizeMs(), totalEvents);
    }

    public List<LockStatistics> getHotLocks(int topN) {
        long windowSize = dynamicWindow.getCurrentWindowSizeMs();
        long now = System.currentTimeMillis();
        long windowStart = now - windowSize;

        return lockStatisticsMap.values().stream()
                .filter(s -> s.getEventCountInWindow(windowStart) >= dynamicWindow.getHotLockThreshold())
                .sorted(Comparator.comparingLong((LockStatistics s) -> s.getEventCountInWindow(windowStart)).reversed())
                .limit(topN)
                .collect(Collectors.toList());
    }

    public List<LockStatistics> getHighContentionLocks(int topN) {
        return lockStatisticsMap.values().stream()
                .filter(s -> s.getContentionRate() > 0.1)
                .sorted(Comparator.comparingDouble(LockStatistics::getContentionRate).reversed())
                .limit(topN)
                .collect(Collectors.toList());
    }

    public Map<String, Object> getLockStatistics(String lockKey) {
        LockStatistics stats = lockStatisticsMap.get(lockKey);
        if (stats == null) {
            return new HashMap<>();
        }

        Map<String, Object> result = new HashMap<>();
        result.put("lockKey", stats.getLockKey());
        result.put("lockType", stats.getLockType());
        result.put("acquireCount", stats.getAcquireCount());
        result.put("failCount", stats.getFailCount());
        result.put("contentionCount", stats.getContentionCount());
        result.put("contentionRate", stats.getContentionRate());
        result.put("avgWaitTimeMs", stats.getAvgWaitTimeMs());
        result.put("avgHoldTimeMs", stats.getAvgHoldTimeMs());
        result.put("maxWaitTimeMs", stats.getMaxWaitTimeMs());
        result.put("maxHoldTimeMs", stats.getMaxHoldTimeMs());
        result.put("activeHolders", stats.getActiveHolderCount());
        result.put("isDirty", dirtyLocks.contains(lockKey));
        return result;
    }

    public List<DeadlockInfo> detectPotentialDeadlocks() {
        if (System.currentTimeMillis() - lastDeadlockAnalysisTime > 5000) {
            cachedDeadlockResults = deadlockDetector.detectDeadlocksIncremental(dirtyLocks);
            lastDeadlockAnalysisTime = System.currentTimeMillis();
        }
        return new ArrayList<>(cachedDeadlockResults);
    }

    public Map<String, Object> getOverallStatistics() {
        Map<String, Object> result = new HashMap<>();
        long totalAcquires = 0;
        long totalFails = 0;
        long totalContentions = 0;
        double totalAvgWaitTime = 0;
        int lockCount = lockStatisticsMap.size();

        for (LockStatistics stats : lockStatisticsMap.values()) {
            totalAcquires += stats.getAcquireCount();
            totalFails += stats.getFailCount();
            totalContentions += stats.getContentionCount();
            totalAvgWaitTime += stats.getAvgWaitTimeMs();
        }

        long hotLockThreshold = dynamicWindow.getHotLockThreshold();

        result.put("totalLocks", lockCount);
        result.put("totalAcquires", totalAcquires);
        result.put("totalFails", totalFails);
        result.put("totalContentions", totalContentions);
        result.put("overallFailureRate", totalAcquires > 0 ? (double) totalFails / totalAcquires : 0);
        result.put("overallContentionRate", totalAcquires > 0 ? (double) totalContentions / totalAcquires : 0);
        result.put("avgWaitTimeAcrossLocks", lockCount > 0 ? totalAvgWaitTime / lockCount : 0);
        result.put("hotLocksCount", lockStatisticsMap.values().stream()
                .filter(s -> s.getAcquireCount() >= hotLockThreshold).count());
        result.put("highContentionLocksCount", lockStatisticsMap.values().stream()
                .filter(s -> s.getContentionRate() > 0.1).count());
        result.put("dirtyLocksCount", dirtyLocks.size());
        result.put("dynamicWindowSizeMs", dynamicWindow.getCurrentWindowSizeMs());
        result.put("hotLockThreshold", hotLockThreshold);

        return result;
    }

    public Map<String, Object> getDynamicWindowInfo() {
        Map<String, Object> info = new HashMap<>();
        info.put("currentWindowSizeMs", dynamicWindow.getCurrentWindowSizeMs());
        info.put("hotLockThreshold", dynamicWindow.getHotLockThreshold());
        info.put("eventsInLastMinute", dynamicWindow.getTotalEventsInLastMinute());
        info.put("windowLevel", dynamicWindow.getCurrentLevel());
        return info;
    }

    public ConcurrentHashMap<String, LockStatistics> getLockStatisticsMap() {
        return lockStatisticsMap;
    }

    public static class DynamicWindow {
        private static final long MIN_WINDOW_MS = 10000;
        private static final long DEFAULT_WINDOW_MS = 60000;
        private static final long MAX_WINDOW_MS = 300000;

        private static final long LOW_TRAFFIC_THRESHOLD = 100;
        private static final long HIGH_TRAFFIC_THRESHOLD = 5000;
        private static final long VERY_HIGH_TRAFFIC_THRESHOLD = 20000;

        private volatile long currentWindowSizeMs = DEFAULT_WINDOW_MS;
        private final AtomicLong eventsInLastMinute = new AtomicLong(0);
        private final LinkedList<Long> eventTimestamps = new LinkedList<>();
        private volatile int currentLevel = 2;

        public synchronized void recordEvent(String lockKey, long timestamp) {
            eventTimestamps.add(timestamp);
            eventsInLastMinute.incrementAndGet();

            long cutoff = System.currentTimeMillis() - 60000;
            while (!eventTimestamps.isEmpty() && eventTimestamps.getFirst() < cutoff) {
                eventTimestamps.removeFirst();
                eventsInLastMinute.decrementAndGet();
            }
        }

        public synchronized void adjustWindowSize(long eventsPerMinute) {
            int newLevel;
            if (eventsPerMinute > VERY_HIGH_TRAFFIC_THRESHOLD) {
                newLevel = 0;
                currentWindowSizeMs = MIN_WINDOW_MS;
            } else if (eventsPerMinute > HIGH_TRAFFIC_THRESHOLD) {
                newLevel = 1;
                currentWindowSizeMs = 30000;
            } else if (eventsPerMinute > LOW_TRAFFIC_THRESHOLD) {
                newLevel = 2;
                currentWindowSizeMs = DEFAULT_WINDOW_MS;
            } else {
                newLevel = 3;
                currentWindowSizeMs = MAX_WINDOW_MS;
            }

            if (newLevel != currentLevel) {
                currentLevel = newLevel;
                logger.info("Dynamic window adjusted to level {} ({}ms) based on traffic: {} events/min",
                        newLevel, currentWindowSizeMs, eventsPerMinute);
            }
        }

        public long getCurrentWindowSizeMs() {
            return currentWindowSizeMs;
        }

        public long getTotalEventsInLastMinute() {
            return eventsInLastMinute.get();
        }

        public long getHotLockThreshold() {
            if (currentLevel == 0) {
                return 50;
            } else if (currentLevel == 1) {
                return 75;
            } else if (currentLevel == 2) {
                return 100;
            } else {
                return 150;
            }
        }

        public int getCurrentLevel() {
            return currentLevel;
        }
    }

    public static class IncrementalDeadlockDetector {
        private final ConcurrentHashMap<String, LockState> lockStates = new ConcurrentHashMap<>();
        private final ConcurrentHashMap<String, Set<String>> waitForGraph = new ConcurrentHashMap<>();

        public void updateLockState(String lockKey, LockStatistics stats) {
            LockState state = lockStates.computeIfAbsent(lockKey, k -> new LockState(lockKey));
            state.updateFromStatistics(stats);
        }

        public List<DeadlockInfo> detectDeadlocksIncremental(Set<String> changedLocks) {
            List<DeadlockInfo> results = new ArrayList<>();

            for (String lockKey : changedLocks) {
                LockState state = lockStates.get(lockKey);
                if (state == null) {
                    continue;
                }

                DeadlockInfo info = analyzeSingleLock(state);
                if (info != null) {
                    results.add(info);
                }
            }

            return results;
        }

        private DeadlockInfo analyzeSingleLock(LockState state) {
            if (state.activeHolders.size() <= 1) {
                return null;
            }

            long avgHoldTime = state.getAvgHoldTime();
            long maxHoldTime = state.getMaxHoldTime();
            int activeHolderCount = state.activeHolders.size();

            boolean highRisk = activeHolderCount > 5 && avgHoldTime > 10000;
            boolean mediumRisk = activeHolderCount > 3 && avgHoldTime > 5000;

            if (!highRisk && !mediumRisk) {
                return null;
            }

            DeadlockInfo info = new DeadlockInfo();
            info.setLockKey(state.lockKey);
            info.setRiskLevel(highRisk ? "HIGH" : "MEDIUM");
            info.setDescription(String.format(
                    "Lock %s has %d active holders, avg hold time %.2fms, max hold time %dms. Potential deadlock risk.",
                    state.lockKey, activeHolderCount, (double) avgHoldTime, maxHoldTime));
            info.setActiveHolderCount(activeHolderCount);
            info.setAvgHoldTimeMs(avgHoldTime);
            info.setMaxHoldTimeMs(maxHoldTime);

            return info;
        }

        private static class LockState {
            final String lockKey;
            final Map<String, HolderInfo> activeHolders = new ConcurrentHashMap<>();
            long totalHoldTime = 0;
            long maxHoldTime = 0;
            long holdCount = 0;

            LockState(String lockKey) {
                this.lockKey = lockKey;
            }

            void updateFromStatistics(LockStatistics stats) {
                activeHolders.putAll(stats.getActiveHolders());
                this.totalHoldTime = stats.totalHoldTime;
                this.holdCount = stats.acquireCount;
                this.maxHoldTime = stats.maxHoldTime;
            }

            long getAvgHoldTime() {
                return holdCount > 0 ? totalHoldTime / holdCount : 0;
            }

            long getMaxHoldTime() {
                return maxHoldTime;
            }
        }
    }

    public static class LockStatistics {
        private static final int MAX_WAIT_SAMPLES = 1000;
        private static final int MAX_HOLD_SAMPLES = 1000;

        private final String lockKey;
        private final String lockType;
        private long acquireCount = 0;
        private long failCount = 0;
        private long contentionCount = 0;
        private long totalWaitTime = 0;
        long totalHoldTime = 0;
        private long maxWaitTime = 0;
        long maxHoldTime = 0;

        private final Map<String, HolderInfo> activeHolders = new ConcurrentHashMap<>();
        private final LinkedList<Long> eventTimestamps = new LinkedList<>();
        private final LinkedList<WaitTimeSample> waitTimeSamples = new LinkedList<>();
        private final LinkedList<Long> holdTimeSamples = new LinkedList<>();

        public LockStatistics(String lockKey, String lockType) {
            this.lockKey = lockKey;
            this.lockType = lockType;
        }

        public synchronized void incrementAcquireCount() {
            acquireCount++;
            eventTimestamps.add(System.currentTimeMillis());
            cleanupOldEvents();
        }

        public synchronized void incrementFailCount() {
            failCount++;
        }

        public synchronized void incrementContentionCount() {
            contentionCount++;
        }

        public synchronized void addWaitTime(long waitTime) {
            totalWaitTime += waitTime;
            if (waitTime > maxWaitTime) {
                maxWaitTime = waitTime;
            }
            waitTimeSamples.add(new WaitTimeSample(waitTime, System.currentTimeMillis()));
            while (waitTimeSamples.size() > MAX_WAIT_SAMPLES) {
                waitTimeSamples.removeFirst();
            }
        }

        public synchronized void addHoldTime(long holdTime) {
            totalHoldTime += holdTime;
            if (holdTime > maxHoldTime) {
                maxHoldTime = holdTime;
            }
            holdTimeSamples.add(holdTime);
            while (holdTimeSamples.size() > MAX_HOLD_SAMPLES) {
                holdTimeSamples.removeFirst();
            }
        }

        public void recordAcquire(String ownerId, String threadId, long timestamp) {
            activeHolders.put(ownerId, new HolderInfo(ownerId, threadId, timestamp));
        }

        public void recordRelease(String ownerId, long timestamp) {
            activeHolders.remove(ownerId);
        }

        public int getActiveHolderCount() {
            return activeHolders.size();
        }

        public Map<String, HolderInfo> getActiveHolders() {
            return new HashMap<>(activeHolders);
        }

        private void cleanupOldEvents() {
            long cutoff = System.currentTimeMillis() - 300000;
            while (!eventTimestamps.isEmpty() && eventTimestamps.getFirst() < cutoff) {
                eventTimestamps.removeFirst();
            }
        }

        public synchronized long getEventCountInWindow(long windowStart) {
            long count = 0;
            for (int i = eventTimestamps.size() - 1; i >= 0; i--) {
                if (eventTimestamps.get(i) >= windowStart) {
                    count++;
                } else {
                    break;
                }
            }
            return count;
        }

        public synchronized List<Long> getRecentWaitTimes(int count) {
            List<Long> recent = new ArrayList<>();
            for (int i = waitTimeSamples.size() - 1; i >= 0 && recent.size() < count; i--) {
                recent.add(waitTimeSamples.get(i).waitTimeMs);
            }
            return recent;
        }

        public synchronized List<Long> getRecentHoldTimes(int count) {
            List<Long> recent = new ArrayList<>();
            for (int i = holdTimeSamples.size() - 1; i >= 0 && recent.size() < count; i--) {
                recent.add(holdTimeSamples.get(i));
            }
            return recent;
        }

        public synchronized double getWaitTimePercentile(double percentile) {
            if (waitTimeSamples.isEmpty()) {
                return 0;
            }
            List<Long> sorted = waitTimeSamples.stream()
                    .map(s -> s.waitTimeMs)
                    .sorted()
                    .collect(Collectors.toList());
            int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
            return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
        }

        public synchronized double getHoldTimePercentile(double percentile) {
            if (holdTimeSamples.isEmpty()) {
                return 0;
            }
            List<Long> sorted = holdTimeSamples.stream()
                    .sorted()
                    .collect(Collectors.toList());
            int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
            return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
        }

        public synchronized double getRecentContentionRate(long windowMs) {
            long cutoff = System.currentTimeMillis() - windowMs;
            long recentAcquires = 0;
            long recentFails = 0;
            for (WaitTimeSample sample : waitTimeSamples) {
                if (sample.timestamp >= cutoff) {
                    recentAcquires++;
                }
            }
            if (recentAcquires == 0) {
                return 0;
            }
            return (double) recentFails / recentAcquires;
        }

        public String getLockKey() {
            return lockKey;
        }

        public String getLockType() {
            return lockType;
        }

        public long getAcquireCount() {
            return acquireCount;
        }

        public long getFailCount() {
            return failCount;
        }

        public long getContentionCount() {
            return contentionCount;
        }

        public double getContentionRate() {
            return acquireCount > 0 ? (double) contentionCount / acquireCount : 0;
        }

        public double getAvgWaitTimeMs() {
            return acquireCount > 0 ? (double) totalWaitTime / acquireCount : 0;
        }

        public double getAvgHoldTimeMs() {
            return acquireCount > 0 ? (double) totalHoldTime / acquireCount : 0;
        }

        public long getMaxWaitTimeMs() {
            return maxWaitTime;
        }

        public long getMaxHoldTimeMs() {
            return maxHoldTime;
        }
    }

    public static class WaitTimeSample {
        final long waitTimeMs;
        final long timestamp;

        public WaitTimeSample(long waitTimeMs, long timestamp) {
            this.waitTimeMs = waitTimeMs;
            this.timestamp = timestamp;
        }
    }

    public static class HolderInfo {
        final String ownerId;
        final String threadId;
        final long acquireTime;

        public HolderInfo(String ownerId, String threadId, long acquireTime) {
            this.ownerId = ownerId;
            this.threadId = threadId;
            this.acquireTime = acquireTime;
        }

        public long getHoldDuration() {
            return System.currentTimeMillis() - acquireTime;
        }
    }

    public static class DeadlockInfo {
        private String lockKey;
        private String riskLevel;
        private String description;
        private int activeHolderCount;
        private long avgHoldTimeMs;
        private long maxHoldTimeMs;

        public String getLockKey() {
            return lockKey;
        }

        public void setLockKey(String lockKey) {
            this.lockKey = lockKey;
        }

        public String getRiskLevel() {
            return riskLevel;
        }

        public void setRiskLevel(String riskLevel) {
            this.riskLevel = riskLevel;
        }

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public int getActiveHolderCount() {
            return activeHolderCount;
        }

        public void setActiveHolderCount(int activeHolderCount) {
            this.activeHolderCount = activeHolderCount;
        }

        public long getAvgHoldTimeMs() {
            return avgHoldTimeMs;
        }

        public void setAvgHoldTimeMs(long avgHoldTimeMs) {
            this.avgHoldTimeMs = avgHoldTimeMs;
        }

        public long getMaxHoldTimeMs() {
            return maxHoldTimeMs;
        }

        public void setMaxHoldTimeMs(long maxHoldTimeMs) {
            this.maxHoldTimeMs = maxHoldTimeMs;
        }
    }

    public static class LockHoldInfo {
        private String lockKey;
        private String threadId;
        private long acquireTime;

        public String getLockKey() {
            return lockKey;
        }

        public void setLockKey(String lockKey) {
            this.lockKey = lockKey;
        }

        public String getThreadId() {
            return threadId;
        }

        public void setThreadId(String threadId) {
            this.threadId = threadId;
        }

        public long getAcquireTime() {
            return acquireTime;
        }

        public void setAcquireTime(long acquireTime) {
            this.acquireTime = acquireTime;
        }
    }
}
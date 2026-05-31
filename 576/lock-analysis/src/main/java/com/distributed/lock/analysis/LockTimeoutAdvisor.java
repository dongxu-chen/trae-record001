package com.distributed.lock.analysis;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class LockTimeoutAdvisor {

    private static final Logger logger = LoggerFactory.getLogger(LockTimeoutAdvisor.class);

    private static final long DEFAULT_WAIT_TIMEOUT_MS = 5000;
    private static final long DEFAULT_LEASE_TIMEOUT_MS = 30000;
    private static final long MIN_WAIT_TIMEOUT_MS = 100;
    private static final long MAX_WAIT_TIMEOUT_MS = 60000;
    private static final long MIN_LEASE_TIMEOUT_MS = 1000;
    private static final long MAX_LEASE_TIMEOUT_MS = 300000;
    private static final double TIMEOUT_BUFFER_FACTOR = 1.5;
    private static final double LEASE_BUFFER_FACTOR = 2.0;
    private static final int MIN_SAMPLES = 20;

    private final LockAnalysisService analysisService;
    private final LockWaitPredictor waitPredictor;

    private final ConcurrentHashMap<String, TimeoutConfig> currentTimeouts = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, TimeoutConfig> recommendedTimeouts = new ConcurrentHashMap<>();

    public LockTimeoutAdvisor(LockAnalysisService analysisService, LockWaitPredictor waitPredictor) {
        this.analysisService = analysisService;
        this.waitPredictor = waitPredictor;
    }

    public TimeoutAdvice getTimeoutAdvice(String lockKey) {
        LockAnalysisService.LockStatistics stats = analysisService.getLockStatisticsMap().get(lockKey);

        TimeoutAdvice advice = new TimeoutAdvice();
        advice.setLockKey(lockKey);

        if (stats == null || stats.getAcquireCount() < MIN_SAMPLES) {
            advice.setHasEnoughData(false);
            advice.setRecommendedWaitTimeoutMs(DEFAULT_WAIT_TIMEOUT_MS);
            advice.setRecommendedLeaseTimeoutMs(DEFAULT_LEASE_TIMEOUT_MS);
            advice.setReason(stats == null ? "No statistics available"
                    : String.format("Insufficient samples (%d < %d)", stats.getAcquireCount(), MIN_SAMPLES));
            return advice;
        }

        advice.setHasEnoughData(true);

        List<Long> recentWaitTimes = stats.getRecentWaitTimes(200);
        List<Long> recentHoldTimes = stats.getRecentHoldTimes(200);

        long recommendedWait = calculateWaitTimeout(recentWaitTimes, stats);
        long recommendedLease = calculateLeaseTimeout(recentHoldTimes, stats);

        advice.setRecommendedWaitTimeoutMs(recommendedWait);
        advice.setRecommendedLeaseTimeoutMs(recommendedLease);

        TimeoutConfig current = currentTimeouts.get(lockKey);
        if (current != null) {
            advice.setCurrentWaitTimeoutMs(current.getWaitTimeoutMs());
            advice.setCurrentLeaseTimeoutMs(current.getLeaseTimeoutMs());
            advice.setWaitTimeoutChangeMs(recommendedWait - current.getWaitTimeoutMs());
            advice.setLeaseTimeoutChangeMs(recommendedLease - current.getLeaseTimeoutMs());
        }

        advice.setWaitTimeP50(calculatePercentile(recentWaitTimes, 50));
        advice.setWaitTimeP90(calculatePercentile(recentWaitTimes, 90));
        advice.setWaitTimeP95(calculatePercentile(recentWaitTimes, 95));
        advice.setHoldTimeP50(calculatePercentile(recentHoldTimes, 50));
        advice.setHoldTimeP90(calculatePercentile(recentHoldTimes, 90));
        advice.setHoldTimeP95(calculatePercentile(recentHoldTimes, 95));

        double contentionRate = stats.getContentionRate();
        advice.setContentionRate(contentionRate);
        advice.setTimeoutStrategy(determineTimeoutStrategy(stats, recommendedWait, recommendedLease));

        TimeoutConfig recommended = new TimeoutConfig(recommendedWait, recommendedLease);
        recommendedTimeouts.put(lockKey, recommended);

        return advice;
    }

    public Map<String, TimeoutAdvice> getAllTimeoutAdvice() {
        Map<String, TimeoutAdvice> allAdvice = new HashMap<>();
        for (String lockKey : analysisService.getLockStatisticsMap().keySet()) {
            allAdvice.put(lockKey, getTimeoutAdvice(lockKey));
        }
        return allAdvice;
    }

    public void applyTimeout(String lockKey, long waitTimeoutMs, long leaseTimeoutMs) {
        waitTimeoutMs = clamp(waitTimeoutMs, MIN_WAIT_TIMEOUT_MS, MAX_WAIT_TIMEOUT_MS);
        leaseTimeoutMs = clamp(leaseTimeoutMs, MIN_LEASE_TIMEOUT_MS, MAX_LEASE_TIMEOUT_MS);

        TimeoutConfig config = new TimeoutConfig(waitTimeoutMs, leaseTimeoutMs);
        currentTimeouts.put(lockKey, config);

        logger.info("Applied timeout for lock {}: wait={}ms, lease={}ms", lockKey, waitTimeoutMs, leaseTimeoutMs);
    }

    public void applyRecommendedTimeout(String lockKey) {
        TimeoutConfig recommended = recommendedTimeouts.get(lockKey);
        if (recommended != null) {
            currentTimeouts.put(lockKey, recommended);
            logger.info("Applied recommended timeout for lock {}: wait={}ms, lease={}ms",
                    lockKey, recommended.getWaitTimeoutMs(), recommended.getLeaseTimeoutMs());
        }
    }

    public TimeoutConfig getCurrentTimeout(String lockKey) {
        return currentTimeouts.getOrDefault(lockKey, new TimeoutConfig(DEFAULT_WAIT_TIMEOUT_MS, DEFAULT_LEASE_TIMEOUT_MS));
    }

    public Map<String, TimeoutConfig> getAllCurrentTimeouts() {
        return new HashMap<>(currentTimeouts);
    }

    public List<TimeoutAdjustmentLog> getRecentAdjustments() {
        List<TimeoutAdjustmentLog> logs = new ArrayList<>();
        for (Map.Entry<String, TimeoutConfig> entry : currentTimeouts.entrySet()) {
            TimeoutConfig recommended = recommendedTimeouts.get(entry.getKey());
            if (recommended != null) {
                TimeoutAdjustmentLog log = new TimeoutAdjustmentLog();
                log.setLockKey(entry.getKey());
                log.setCurrentWaitMs(entry.getValue().getWaitTimeoutMs());
                log.setCurrentLeaseMs(entry.getValue().getLeaseTimeoutMs());
                log.setRecommendedWaitMs(recommended.getWaitTimeoutMs());
                log.setRecommendedLeaseMs(recommended.getLeaseTimeoutMs());
                log.setNeedsAdjustment(
                        Math.abs(entry.getValue().getWaitTimeoutMs() - recommended.getWaitTimeoutMs()) > entry.getValue().getWaitTimeoutMs() * 0.2
                                || Math.abs(entry.getValue().getLeaseTimeoutMs() - recommended.getLeaseTimeoutMs()) > entry.getValue().getLeaseTimeoutMs() * 0.2
                );
                logs.add(log);
            }
        }
        return logs;
    }

    private long calculateWaitTimeout(List<Long> waitTimes, LockAnalysisService.LockStatistics stats) {
        if (waitTimes.isEmpty()) {
            return DEFAULT_WAIT_TIMEOUT_MS;
        }

        double p90 = calculatePercentile(waitTimes, 90);
        double p95 = calculatePercentile(waitTimes, 95);

        double baseTimeout = Math.max(p90, p95);

        double adjusted = baseTimeout * TIMEOUT_BUFFER_FACTOR;

        double contentionRate = stats.getContentionRate();
        if (contentionRate > 0.5) {
            adjusted *= 1.5;
        } else if (contentionRate > 0.3) {
            adjusted *= 1.2;
        }

        return clamp((long) adjusted, MIN_WAIT_TIMEOUT_MS, MAX_WAIT_TIMEOUT_MS);
    }

    private long calculateLeaseTimeout(List<Long> holdTimes, LockAnalysisService.LockStatistics stats) {
        if (holdTimes.isEmpty()) {
            return DEFAULT_LEASE_TIMEOUT_MS;
        }

        double p95 = calculatePercentile(holdTimes, 95);
        double p99 = calculatePercentile(holdTimes, 99);

        double baseTimeout = Math.max(p95, p99);

        double adjusted = baseTimeout * LEASE_BUFFER_FACTOR;

        double holdTimeStdDev = calculateStdDev(holdTimes);
        double avgHold = stats.getAvgHoldTimeMs();
        if (avgHold > 0 && holdTimeStdDev / avgHold > 1.0) {
            adjusted *= 1.3;
        }

        return clamp((long) adjusted, MIN_LEASE_TIMEOUT_MS, MAX_LEASE_TIMEOUT_MS);
    }

    private String determineTimeoutStrategy(LockAnalysisService.LockStatistics stats, long recommendedWait, long recommendedLease) {
        double contentionRate = stats.getContentionRate();
        double avgHold = stats.getAvgHoldTimeMs();

        if (contentionRate > 0.5 && avgHold > 3000) {
            return "AGGRESSIVE_TIMEOUT: High contention + long hold time. Set aggressive timeouts to fail fast and reduce queue buildup.";
        } else if (contentionRate > 0.3) {
            return "MODERATE_TIMEOUT: Moderate contention. Use p95-based timeouts with small buffer.";
        } else if (avgHold > 5000) {
            return "LONG_LEASE: Low contention but long hold time. Focus on generous lease timeouts to prevent premature expiration.";
        } else {
            return "STANDARD_TIMEOUT: Normal lock behavior. Standard p90/p95 based timeouts are sufficient.";
        }
    }

    private double calculatePercentile(List<Long> values, double percentile) {
        if (values.isEmpty()) {
            return 0;
        }
        List<Long> sorted = new ArrayList<>(values);
        sorted.sort(Long::compare);
        int index = (int) Math.ceil(percentile / 100.0 * sorted.size()) - 1;
        return sorted.get(Math.max(0, Math.min(index, sorted.size() - 1)));
    }

    private double calculateStdDev(List<Long> values) {
        if (values.isEmpty()) {
            return 0;
        }
        double avg = values.stream().mapToLong(l -> l).average().orElse(0);
        double variance = values.stream()
                .mapToDouble(l -> Math.pow(l - avg, 2))
                .average().orElse(0);
        return Math.sqrt(variance);
    }

    private long clamp(long value, long min, long max) {
        return Math.max(min, Math.min(max, value));
    }

    public static class TimeoutConfig {
        private final long waitTimeoutMs;
        private final long leaseTimeoutMs;

        public TimeoutConfig(long waitTimeoutMs, long leaseTimeoutMs) {
            this.waitTimeoutMs = waitTimeoutMs;
            this.leaseTimeoutMs = leaseTimeoutMs;
        }

        public long getWaitTimeoutMs() {
            return waitTimeoutMs;
        }

        public long getLeaseTimeoutMs() {
            return leaseTimeoutMs;
        }
    }

    public static class TimeoutAdvice {
        private String lockKey;
        private boolean hasEnoughData;
        private String reason;
        private long recommendedWaitTimeoutMs;
        private long recommendedLeaseTimeoutMs;
        private Long currentWaitTimeoutMs;
        private Long currentLeaseTimeoutMs;
        private Long waitTimeoutChangeMs;
        private Long leaseTimeoutChangeMs;
        private double waitTimeP50;
        private double waitTimeP90;
        private double waitTimeP95;
        private double holdTimeP50;
        private double holdTimeP90;
        private double holdTimeP95;
        private double contentionRate;
        private String timeoutStrategy;

        public String getLockKey() { return lockKey; }
        public void setLockKey(String lockKey) { this.lockKey = lockKey; }
        public boolean isHasEnoughData() { return hasEnoughData; }
        public void setHasEnoughData(boolean hasEnoughData) { this.hasEnoughData = hasEnoughData; }
        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
        public long getRecommendedWaitTimeoutMs() { return recommendedWaitTimeoutMs; }
        public void setRecommendedWaitTimeoutMs(long recommendedWaitTimeoutMs) { this.recommendedWaitTimeoutMs = recommendedWaitTimeoutMs; }
        public long getRecommendedLeaseTimeoutMs() { return recommendedLeaseTimeoutMs; }
        public void setRecommendedLeaseTimeoutMs(long recommendedLeaseTimeoutMs) { this.recommendedLeaseTimeoutMs = recommendedLeaseTimeoutMs; }
        public Long getCurrentWaitTimeoutMs() { return currentWaitTimeoutMs; }
        public void setCurrentWaitTimeoutMs(Long currentWaitTimeoutMs) { this.currentWaitTimeoutMs = currentWaitTimeoutMs; }
        public Long getCurrentLeaseTimeoutMs() { return currentLeaseTimeoutMs; }
        public void setCurrentLeaseTimeoutMs(Long currentLeaseTimeoutMs) { this.currentLeaseTimeoutMs = currentLeaseTimeoutMs; }
        public Long getWaitTimeoutChangeMs() { return waitTimeoutChangeMs; }
        public void setWaitTimeoutChangeMs(Long waitTimeoutChangeMs) { this.waitTimeoutChangeMs = waitTimeoutChangeMs; }
        public Long getLeaseTimeoutChangeMs() { return leaseTimeoutChangeMs; }
        public void setLeaseTimeoutChangeMs(Long leaseTimeoutChangeMs) { this.leaseTimeoutChangeMs = leaseTimeoutChangeMs; }
        public double getWaitTimeP50() { return waitTimeP50; }
        public void setWaitTimeP50(double waitTimeP50) { this.waitTimeP50 = waitTimeP50; }
        public double getWaitTimeP90() { return waitTimeP90; }
        public void setWaitTimeP90(double waitTimeP90) { this.waitTimeP90 = waitTimeP90; }
        public double getWaitTimeP95() { return waitTimeP95; }
        public void setWaitTimeP95(double waitTimeP95) { this.waitTimeP95 = waitTimeP95; }
        public double getHoldTimeP50() { return holdTimeP50; }
        public void setHoldTimeP50(double holdTimeP50) { this.holdTimeP50 = holdTimeP50; }
        public double getHoldTimeP90() { return holdTimeP90; }
        public void setHoldTimeP90(double holdTimeP90) { this.holdTimeP90 = holdTimeP90; }
        public double getHoldTimeP95() { return holdTimeP95; }
        public void setHoldTimeP95(double holdTimeP95) { this.holdTimeP95 = holdTimeP95; }
        public double getContentionRate() { return contentionRate; }
        public void setContentionRate(double contentionRate) { this.contentionRate = contentionRate; }
        public String getTimeoutStrategy() { return timeoutStrategy; }
        public void setTimeoutStrategy(String timeoutStrategy) { this.timeoutStrategy = timeoutStrategy; }
    }

    public static class TimeoutAdjustmentLog {
        private String lockKey;
        private long currentWaitMs;
        private long currentLeaseMs;
        private long recommendedWaitMs;
        private long recommendedLeaseMs;
        private boolean needsAdjustment;

        public String getLockKey() { return lockKey; }
        public void setLockKey(String lockKey) { this.lockKey = lockKey; }
        public long getCurrentWaitMs() { return currentWaitMs; }
        public void setCurrentWaitMs(long currentWaitMs) { this.currentWaitMs = currentWaitMs; }
        public long getCurrentLeaseMs() { return currentLeaseMs; }
        public void setCurrentLeaseMs(long currentLeaseMs) { this.currentLeaseMs = currentLeaseMs; }
        public long getRecommendedWaitMs() { return recommendedWaitMs; }
        public void setRecommendedWaitMs(long recommendedWaitMs) { this.recommendedWaitMs = recommendedWaitMs; }
        public long getRecommendedLeaseMs() { return recommendedLeaseMs; }
        public void setRecommendedLeaseMs(long recommendedLeaseMs) { this.recommendedLeaseMs = recommendedLeaseMs; }
        public boolean isNeedsAdjustment() { return needsAdjustment; }
        public void setNeedsAdjustment(boolean needsAdjustment) { this.needsAdjustment = needsAdjustment; }
    }
}
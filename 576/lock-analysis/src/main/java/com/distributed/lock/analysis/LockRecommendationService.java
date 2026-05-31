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
public class LockRecommendationService {

    private static final Logger logger = LoggerFactory.getLogger(LockRecommendationService.class);

    private static final long HIGH_HOLD_TIME_THRESHOLD_MS = 500;
    private static final double HIGH_CONTENTION_THRESHOLD = 0.2;
    private static final long HIGH_FREQUENCY_THRESHOLD = 500;
    private static final double COARSE_GRAIN_SCORE_THRESHOLD = 0.6;

    private final LockAnalysisService analysisService;

    public LockRecommendationService(LockAnalysisService analysisService) {
        this.analysisService = analysisService;
    }

    public List<LockRecommendation> analyzeLockGranularity() {
        List<LockRecommendation> recommendations = new ArrayList<>();
        Map<String, LockAnalysisService.LockStatistics> statsMap = analysisService.getLockStatisticsMap();

        for (Map.Entry<String, LockAnalysisService.LockStatistics> entry : statsMap.entrySet()) {
            String lockKey = entry.getKey();
            LockAnalysisService.LockStatistics stats = entry.getValue();

            double coarseScore = calculateCoarseGrainScore(stats);

            if (coarseScore >= COARSE_GRAIN_SCORE_THRESHOLD) {
                LockRecommendation rec = buildRecommendation(lockKey, stats, coarseScore);
                recommendations.add(rec);
            }
        }

        recommendations.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));
        return recommendations;
    }

    public LockRecommendation getRecommendation(String lockKey) {
        LockAnalysisService.LockStatistics stats = analysisService.getLockStatisticsMap().get(lockKey);
        if (stats == null) {
            return null;
        }

        double coarseScore = calculateCoarseGrainScore(stats);
        return buildRecommendation(lockKey, stats, coarseScore);
    }

    private double calculateCoarseGrainScore(LockAnalysisService.LockStatistics stats) {
        double score = 0;

        double avgHoldTime = stats.getAvgHoldTimeMs();
        if (avgHoldTime > 5000) {
            score += 0.35;
        } else if (avgHoldTime > 2000) {
            score += 0.25;
        } else if (avgHoldTime > HIGH_HOLD_TIME_THRESHOLD_MS) {
            score += 0.15;
        }

        double contentionRate = stats.getContentionRate();
        if (contentionRate > 0.5) {
            score += 0.3;
        } else if (contentionRate > 0.3) {
            score += 0.2;
        } else if (contentionRate > HIGH_CONTENTION_THRESHOLD) {
            score += 0.1;
        }

        double p99HoldTime = stats.getHoldTimePercentile(99);
        double avgHold = stats.getAvgHoldTimeMs();
        if (avgHold > 0 && p99HoldTime / avgHold > 10) {
            score += 0.2;
        } else if (avgHold > 0 && p99HoldTime / avgHold > 5) {
            score += 0.1;
        }

        if (stats.getAcquireCount() > HIGH_FREQUENCY_THRESHOLD && avgHoldTime > 1000) {
            score += 0.15;
        }

        return Math.min(score, 1.0);
    }

    private LockRecommendation buildRecommendation(String lockKey, LockAnalysisService.LockStatistics stats, double score) {
        LockRecommendation rec = new LockRecommendation();
        rec.setLockKey(lockKey);
        rec.setLockType(stats.getLockType());
        rec.setScore(score);
        rec.setLevel(score >= 0.8 ? "CRITICAL" : score >= 0.6 ? "WARNING" : "INFO");

        List<String> suggestions = new ArrayList<>();
        List<String> strategies = new ArrayList<>();

        if (stats.getAvgHoldTimeMs() > 5000) {
            suggestions.add(String.format(
                    "Lock hold time is too long (avg=%.1fms). The lock covers too much business logic.",
                    stats.getAvgHoldTimeMs()));
            strategies.add("Extract non-critical logic outside the lock scope. Only protect the minimum critical section.");
            strategies.add(String.format(
                    "Target hold time: < %.1fms (current avg * 0.1)", stats.getAvgHoldTimeMs()));
        }

        if (stats.getContentionRate() > HIGH_CONTENTION_THRESHOLD) {
            suggestions.add(String.format(
                    "High contention rate (%.1f%%). Multiple threads compete for the same lock frequently.",
                    stats.getContentionRate() * 100));
            strategies.add("Consider lock striping: split into multiple fine-grained locks by partition key.");
            strategies.add("Consider using read-write lock if operations are mostly reads.");
            strategies.add(generateStripingSuggestion(lockKey, stats.getContentionRate()));
        }

        double p99Hold = stats.getHoldTimePercentile(99);
        double avgHold = stats.getAvgHoldTimeMs();
        if (avgHold > 0 && p99Hold / avgHold > 5) {
            suggestions.add(String.format(
                    "High hold time variance (p99=%.1fms, avg=%.1fms, ratio=%.1f). " +
                    "Some operations hold the lock much longer than others.",
                    p99Hold, avgHold, p99Hold / avgHold));
            strategies.add("Separate fast and slow code paths. Use different locks for different operations.");
        }

        if (lockKey.contains(":") || lockKey.contains("/")) {
            strategies.add(String.format(
                    "Current key pattern '%s' suggests composite key. " +
                    "Consider splitting into independent locks per resource type.", lockKey));
        }

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("avgHoldTimeMs", stats.getAvgHoldTimeMs());
        metrics.put("p99HoldTimeMs", stats.getHoldTimePercentile(99));
        metrics.put("contentionRate", stats.getContentionRate());
        metrics.put("acquireCount", stats.getAcquireCount());
        metrics.put("failCount", stats.getFailCount());
        metrics.put("avgWaitTimeMs", stats.getAvgWaitTimeMs());
        metrics.put("p99WaitTimeMs", stats.getWaitTimePercentile(99));

        rec.setSuggestions(suggestions);
        rec.setStrategies(strategies);
        rec.setMetrics(metrics);

        return rec;
    }

    private String generateStripingSuggestion(String lockKey, double contentionRate) {
        int stripeCount = contentionRate > 0.5 ? 16 : contentionRate > 0.3 ? 8 : 4;
        return String.format(
                "Lock striping suggestion: replace '%s' with %d striped locks (e.g. %s:{partitionId})",
                lockKey, stripeCount, lockKey);
    }

    public static class LockRecommendation {
        private String lockKey;
        private String lockType;
        private double score;
        private String level;
        private List<String> suggestions;
        private List<String> strategies;
        private Map<String, Object> metrics;

        public String getLockKey() {
            return lockKey;
        }

        public void setLockKey(String lockKey) {
            this.lockKey = lockKey;
        }

        public String getLockType() {
            return lockType;
        }

        public void setLockType(String lockType) {
            this.lockType = lockType;
        }

        public double getScore() {
            return score;
        }

        public void setScore(double score) {
            this.score = score;
        }

        public String getLevel() {
            return level;
        }

        public void setLevel(String level) {
            this.level = level;
        }

        public List<String> getSuggestions() {
            return suggestions;
        }

        public void setSuggestions(List<String> suggestions) {
            this.suggestions = suggestions;
        }

        public List<String> getStrategies() {
            return strategies;
        }

        public void setStrategies(List<String> strategies) {
            this.strategies = strategies;
        }

        public Map<String, Object> getMetrics() {
            return metrics;
        }

        public void setMetrics(Map<String, Object> metrics) {
            this.metrics = metrics;
        }
    }
}
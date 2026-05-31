package com.drill.platform.scoring;

import com.drill.platform.model.DrillResult;
import com.drill.platform.model.RateLimitStrategy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class ScoringEngine {

    public DrillResult.ScoreDetail calculateScore(DrillResult result, RateLimitStrategy strategy) {
        DrillResult.ScoreDetail detail = new DrillResult.ScoreDetail();

        detail.setAvailabilityScore(calculateAvailabilityScore(result));
        detail.setResponseTimeScore(calculateResponseTimeScore(result));
        detail.setStabilityScore(calculateStabilityScore(result));
        detail.setDegradationEffectScore(calculateDegradationScore(result, strategy));
        detail.setRecoveryScore(calculateRecoveryScore(result));
        detail.setRecoveryTimeScore(calculateRecoveryTimeScore(result));
        detail.setJitterScore(calculateJitterScore(result));
        detail.setOverThresholdScore(calculateOverThresholdScore(result));
        detail.setConsistencyScore(calculateConsistencyScore(result));

        double totalScore = detail.getAvailabilityScore() * 0.20
                + detail.getResponseTimeScore() * 0.15
                + detail.getStabilityScore() * 0.15
                + detail.getDegradationEffectScore() * 0.10
                + detail.getRecoveryScore() * 0.08
                + detail.getRecoveryTimeScore() * 0.12
                + detail.getJitterScore() * 0.08
                + detail.getOverThresholdScore() * 0.07
                + detail.getConsistencyScore() * 0.05;

        result.setScore(Math.round(totalScore * 100.0) / 100.0);
        result.setScoreDetail(detail);

        log.info("Drill scoring complete: total={}, availability={}, responseTime={}, stability={}, degradation={}, recovery={}, recoveryTime={}, jitter={}, overThreshold={}, consistency={}",
                String.format("%.2f", totalScore), String.format("%.2f", detail.getAvailabilityScore()),
                String.format("%.2f", detail.getResponseTimeScore()), String.format("%.2f", detail.getStabilityScore()),
                String.format("%.2f", detail.getDegradationEffectScore()), String.format("%.2f", detail.getRecoveryScore()),
                String.format("%.2f", detail.getRecoveryTimeScore()), String.format("%.2f", detail.getJitterScore()),
                String.format("%.2f", detail.getOverThresholdScore()), String.format("%.2f", detail.getConsistencyScore()));

        return detail;
    }

    private double calculateAvailabilityScore(DrillResult result) {
        if (result.getTotalRequests() == 0) return 0;
        double availability = (double) result.getSuccessRequests() / result.getTotalRequests() * 100;
        if (availability >= 99.9) return 100;
        if (availability >= 99.0) return 90 + (availability - 99.0) * 10;
        if (availability >= 95.0) return 70 + (availability - 95.0) * 4;
        if (availability >= 90.0) return 50 + (availability - 90.0) * 4;
        return availability * 50.0 / 90.0;
    }

    private double calculateResponseTimeScore(DrillResult result) {
        long p95 = result.getP95ResponseTimeMs();
        if (p95 <= 50) return 100;
        if (p95 <= 100) return 95 - (p95 - 50) * 0.1;
        if (p95 <= 200) return 90 - (p95 - 100) * 0.15;
        if (p95 <= 500) return 75 - (p95 - 200) * 0.05;
        if (p95 <= 1000) return 60 - (p95 - 500) * 0.03;
        if (p95 <= 3000) return 45 - (p95 - 1000) * 0.01;
        return Math.max(0, 25 - (p95 - 3000) * 0.005);
    }

    private double calculateStabilityScore(DrillResult result) {
        double errorRate = result.getErrorRate();
        double blockRate = result.getBlockRate();

        double errorPenalty = Math.min(errorRate * 5, 50);
        double blockPenalty = 0;

        if (blockRate > 80) {
            blockPenalty = 30;
        } else if (blockRate > 50) {
            blockPenalty = 15;
        } else if (blockRate > 30) {
            blockPenalty = 5;
        }

        long p99 = result.getP99ResponseTimeMs();
        long p50 = result.getP50ResponseTimeMs();
        double tailLatencyRatio = p50 > 0 ? (double) p99 / p50 : 1;
        double latencyPenalty = tailLatencyRatio > 10 ? 15 : tailLatencyRatio > 5 ? 8 : 0;

        return Math.max(0, 100 - errorPenalty - blockPenalty - latencyPenalty);
    }

    private double calculateDegradationScore(DrillResult result, RateLimitStrategy strategy) {
        double degradationRate = result.getDegradationRate();
        double blockRate = result.getBlockRate();

        if (strategy.getType() == RateLimitStrategy.StrategyType.CIRCUIT_BREAKER) {
            if (degradationRate > 0 && blockRate < 20) return 90;
            if (degradationRate > 0 && blockRate < 40) return 70;
            if (degradationRate > 0) return 50;
        }

        if (strategy.getType() == RateLimitStrategy.StrategyType.DIRECT_REJECT) {
            if (blockRate > 0 && blockRate < 50) return 85;
            if (blockRate >= 50 && blockRate < 80) return 60;
            if (blockRate >= 80) return 30;
        }

        if (degradationRate > 0) return 80;
        if (blockRate > 0) return 70;
        return 50;
    }

    private double calculateRecoveryScore(DrillResult result) {
        if (result.getTotalRequests() == 0) return 50;

        double successRate = (double) result.getSuccessRequests() / result.getTotalRequests();
        if (successRate >= 0.95) return 90;
        if (successRate >= 0.80) return 70;
        if (successRate >= 0.50) return 50;
        return 30;
    }

    private double calculateRecoveryTimeScore(DrillResult result) {
        long recoveryTimeMs = result.getRecoveryTimeMs();
        if (recoveryTimeMs == 0) {
            return result.isAutoRecovered() ? 80 : 60;
        }
        if (recoveryTimeMs <= 1000) return 100;
        if (recoveryTimeMs <= 3000) return 95 - (recoveryTimeMs - 1000) * 0.01;
        if (recoveryTimeMs <= 5000) return 75 - (recoveryTimeMs - 3000) * 0.01;
        if (recoveryTimeMs <= 10000) return 55 - (recoveryTimeMs - 5000) * 0.005;
        return Math.max(0, 30 - (recoveryTimeMs - 10000) * 0.003);
    }

    private double calculateJitterScore(DrillResult result) {
        double jitter = result.getErrorRateJitter();
        if (jitter <= 1) return 100;
        if (jitter <= 3) return 90 - (jitter - 1) * 5;
        if (jitter <= 5) return 80 - (jitter - 3) * 5;
        if (jitter <= 10) return 70 - (jitter - 5) * 3;
        if (jitter <= 20) return 55 - (jitter - 10) * 1.5;
        return Math.max(0, 40 - (jitter - 20) * 0.5);
    }

    private double calculateOverThresholdScore(DrillResult result) {
        int overSeconds = result.getOverThresholdSeconds();
        if (overSeconds == 0) return 100;
        if (overSeconds <= 5) return 90 - overSeconds * 2;
        if (overSeconds <= 15) return 80 - (overSeconds - 5) * 3;
        if (overSeconds <= 30) return 50 - (overSeconds - 15) * 1.5;
        return Math.max(0, 27 - (overSeconds - 30) * 0.5);
    }

    private double calculateConsistencyScore(DrillResult result) {
        double stdDev = result.getResponseTimeStdDev();
        double mean = result.getAvgResponseTimeMs();
        double cv = mean > 0 ? stdDev / mean : 1;

        double baseScore;
        if (cv <= 0.1) baseScore = 100;
        else if (cv <= 0.2) baseScore = 90 - (cv - 0.1) * 100;
        else if (cv <= 0.3) baseScore = 80 - (cv - 0.2) * 100;
        else if (cv <= 0.5) baseScore = 70 - (cv - 0.3) * 50;
        else baseScore = 60 - (cv - 0.5) * 30;

        if (result.isAutoRecovered()) {
            baseScore = Math.min(100, baseScore + 5);
        }

        return Math.max(0, baseScore);
    }
}

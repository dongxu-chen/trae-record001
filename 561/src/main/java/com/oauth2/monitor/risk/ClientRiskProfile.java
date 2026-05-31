package com.oauth2.monitor.risk;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.DoubleAdder;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ClientRiskProfile {

    private String clientId;
    private RiskLevel riskLevel;
    private double riskScore;
    private Instant lastUpdated;
    private Instant firstSeen;

    private AtomicInteger authenticationFailures = new AtomicInteger(0);
    private AtomicInteger authorizationFailures = new AtomicInteger(0);
    private AtomicInteger tokenValidationFailures = new AtomicInteger(0);
    private AtomicInteger bruteForceAttempts = new AtomicInteger(0);
    private AtomicInteger unusualScopeRequests = new AtomicInteger(0);
    private AtomicInteger suspiciousLocations = new AtomicInteger(0);

    private AtomicLong totalRequests = new AtomicLong(0);
    private AtomicLong successfulRequests = new AtomicLong(0);

    private AtomicInteger currentThrottleLevel = new AtomicInteger(0);
    private Instant downgradeUntil;
    private String downgradeReason;

    private DoubleAdder rateLimitViolations = new DoubleAdder();
    private DoubleAdder abuseScoreAccumulator = new DoubleAdder();

    public enum RiskLevel {
        LOW(0, 30, "Low risk - normal behavior"),
        MEDIUM(30, 50, "Medium risk - increased monitoring"),
        HIGH(50, 75, "High risk - rate limiting applied"),
        CRITICAL(75, 90, "Critical risk - strict throttling"),
        BLOCKED(90, 101, "Blocked - security concern");

        private final int minScore;
        private final int maxScore;
        private final String description;

        RiskLevel(int minScore, int maxScore, String description) {
            this.minScore = minScore;
            this.maxScore = maxScore;
            this.description = description;
        }

        public int getMinScore() { return minScore; }
        public int getMaxScore() { return maxScore; }
        public String getDescription() { return description; }

        public static RiskLevel fromScore(double score) {
            if (score >= BLOCKED.minScore) return BLOCKED;
            if (score >= CRITICAL.minScore) return CRITICAL;
            if (score >= HIGH.minScore) return HIGH;
            if (score >= MEDIUM.minScore) return MEDIUM;
            return LOW;
        }
    }

    public enum DowngradeAction {
        NONE("No action"),
        MONITOR("Enhanced monitoring"),
        RATE_LIMIT("Rate limiting applied"),
        THROTTLE("Request throttling"),
        RESTRICT_SCOPES("Scope restrictions"),
        REQUIRE_MFA("MFA required"),
        BLOCK("Access blocked");

        private final String description;

        DowngradeAction(String description) {
            this.description = description;
        }

        public String getDescription() {
            return description;
        }
    }

    public synchronized void calculateRiskScore() {
        double score = 0;
        long total = totalRequests.get();

        if (total > 0) {
            double failureRate = (authenticationFailures.get() + authorizationFailures.get()) * 100.0 / total;
            score += Math.min(failureRate * 2, 40);
        }

        score += Math.min(bruteForceAttempts.get() * 10, 30);
        score += Math.min(unusualScopeRequests.get() * 5, 20);
        score += Math.min(suspiciousLocations.get() * 8, 25);
        score += Math.min(tokenValidationFailures.get() * 3, 15);

        score += Math.min(rateLimitViolations.doubleValue() * 2, 15);

        score += Math.min(abuseScoreAccumulator.doubleValue(), 20);

        if (score > 0 && total > 100) {
            double successRate = successfulRequests.get() * 100.0 / total;
            if (successRate < 50) score += 10;
        }

        score *= 0.95;

        this.riskScore = Math.min(100, Math.max(0, score));
        this.riskLevel = RiskLevel.fromScore(this.riskScore);
        this.lastUpdated = Instant.now();
    }

    public double getSuccessRate() {
        long total = totalRequests.get();
        if (total == 0) return 100.0;
        return successfulRequests.get() * 100.0 / total;
    }

    public boolean isDowngradeActive() {
        return downgradeUntil != null && Instant.now().isBefore(downgradeUntil);
    }

    public DowngradeAction getCurrentDowngradeAction() {
        if (!isDowngradeActive()) return DowngradeAction.NONE;

        return switch (riskLevel) {
            case LOW -> DowngradeAction.MONITOR;
            case MEDIUM -> DowngradeAction.RATE_LIMIT;
            case HIGH -> DowngradeAction.THROTTLE;
            case CRITICAL -> DowngradeAction.RESTRICT_SCOPES;
            case BLOCKED -> DowngradeAction.BLOCK;
        };
    }

    public void recordSuccess() {
        totalRequests.incrementAndGet();
        successfulRequests.incrementAndGet();
    }

    public void recordAuthenticationFailure() {
        totalRequests.incrementAndGet();
        authenticationFailures.incrementAndGet();
    }

    public void recordAuthorizationFailure() {
        totalRequests.incrementAndGet();
        authorizationFailures.incrementAndGet();
    }

    public void recordTokenValidationFailure() {
        totalRequests.incrementAndGet();
        tokenValidationFailures.incrementAndGet();
    }

    public void resetDailyCounters() {
        authenticationFailures.set(0);
        authorizationFailures.set(0);
        tokenValidationFailures.set(0);
        bruteForceAttempts.set(0);
        unusualScopeRequests.set(0);
        suspiciousLocations.set(0);
        rateLimitViolations.reset();
        abuseScoreAccumulator.reset();
    }
}

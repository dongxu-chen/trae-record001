package com.oauth2.monitor.risk;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ClientRiskService {

    private final AlertService alertService;
    private final MeterRegistry meterRegistry;

    @Value("${oauth2.monitor.risk.score-update-interval-seconds:60}")
    private int scoreUpdateIntervalSeconds;

    @Value("${oauth2.monitor.risk.auto-downgrade-enabled:true}")
    private boolean autoDowngradeEnabled;

    @Value("${oauth2.monitor.risk.downgrade-duration-minutes:30}")
    private int downgradeDurationMinutes;

    @Value("${oauth2.monitor.risk.high-risk-threshold:50}")
    private double highRiskThreshold;

    @Value("${oauth2.monitor.risk.critical-risk-threshold:75}")
    private double criticalRiskThreshold;

    private final Map<String, ClientRiskProfile> riskProfiles = new ConcurrentHashMap<>();
    private final Map<String, Counter> riskCounters = new ConcurrentHashMap<>();

    public ClientRiskService(AlertService alertService, MeterRegistry meterRegistry) {
        this.alertService = alertService;
        this.meterRegistry = meterRegistry;

        Gauge.builder("oauth2_risk_client_count_high", () ->
                        riskProfiles.values().stream()
                                .filter(p -> p.getRiskLevel() == ClientRiskProfile.RiskLevel.HIGH).count())
                .description("Number of high risk clients")
                .register(meterRegistry);

        Gauge.builder("oauth2_risk_client_count_critical", () ->
                        riskProfiles.values().stream()
                                .filter(p -> p.getRiskLevel() == ClientRiskProfile.RiskLevel.CRITICAL).count())
                .description("Number of critical risk clients")
                .register(meterRegistry);

        Gauge.builder("oauth2_risk_client_count_blocked", () ->
                        riskProfiles.values().stream()
                                .filter(p -> p.getRiskLevel() == ClientRiskProfile.RiskLevel.BLOCKED).count())
                .description("Number of blocked clients")
                .register(meterRegistry);
    }

    public ClientRiskProfile getOrCreateProfile(String clientId) {
        return riskProfiles.computeIfAbsent(clientId, id -> {
            ClientRiskProfile profile = ClientRiskProfile.builder()
                    .clientId(id)
                    .riskLevel(ClientRiskProfile.RiskLevel.LOW)
                    .riskScore(0.0)
                    .firstSeen(Instant.now())
                    .lastUpdated(Instant.now())
                    .build();

            riskCounters.put(id + "_auth_failures",
                    Counter.builder("oauth2_risk_client_auth_failures")
                            .tag("client_id", id)
                            .register(meterRegistry));

            log.info("Created new risk profile for client: {}", clientId);
            return profile;
        });
    }

    public void recordAuthenticationSuccess(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.recordSuccess();
    }

    public void recordAuthenticationFailure(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.recordAuthenticationFailure();
        riskCounters.computeIfAbsent(clientId + "_auth_failures", k ->
                Counter.builder("oauth2_risk_client_auth_failures")
                        .tag("client_id", clientId)
                        .register(meterRegistry)).increment();
    }

    public void recordAuthorizationFailure(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.recordAuthorizationFailure();
    }

    public void recordTokenValidationFailure(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.recordTokenValidationFailure();
    }

    public void recordBruteForceAttempt(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.getBruteForceAttempts().incrementAndGet();
    }

    public void recordUnusualScopeRequest(String clientId, String scope) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.getUnusualScopeRequests().incrementAndGet();
        profile.getAbuseScoreAccumulator().add(2.0);
    }

    public void recordSuspiciousLocation(String clientId, String location) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.getSuspiciousLocations().incrementAndGet();
        profile.getAbuseScoreAccumulator().add(3.0);
    }

    public void recordRateLimitViolation(String clientId) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.getRateLimitViolations().add(1.0);
    }

    public void recordAbuseScore(String clientId, double score) {
        ClientRiskProfile profile = getOrCreateProfile(clientId);
        profile.getAbuseScoreAccumulator().add(score);
    }

    @Scheduled(fixedDelayString = "${oauth2.monitor.risk.score-update-interval-seconds:60}000")
    public void updateAllRiskScores() {
        log.debug("Updating risk scores for {} clients", riskProfiles.size());

        for (Map.Entry<String, ClientRiskProfile> entry : riskProfiles.entrySet()) {
            String clientId = entry.getKey();
            ClientRiskProfile profile = entry.getValue();

            ClientRiskProfile.RiskLevel previousLevel = profile.getRiskLevel();
            profile.calculateRiskScore();

            if (profile.getRiskLevel() != previousLevel) {
                handleRiskLevelChange(clientId, profile, previousLevel);
            }

            if (autoDowngradeEnabled) {
                checkAndApplyDowngrade(clientId, profile);
            }
        }
    }

    private void handleRiskLevelChange(String clientId, ClientRiskProfile profile,
                                        ClientRiskProfile.RiskLevel previousLevel) {
        log.warn("Risk level changed for client {}: {} -> {} (score: {:.1f})",
                clientId, previousLevel, profile.getRiskLevel(),
                String.format("%.1f", profile.getRiskScore()));

        if (profile.getRiskLevel() == ClientRiskProfile.RiskLevel.HIGH ||
                profile.getRiskLevel() == ClientRiskProfile.RiskLevel.CRITICAL ||
                profile.getRiskLevel() == ClientRiskProfile.RiskLevel.BLOCKED) {

            SecurityEvent.EventType eventType =
                    profile.getRiskLevel() == ClientRiskProfile.RiskLevel.BLOCKED ?
                            SecurityEvent.EventType.SUSPICIOUS_ACTIVITY :
                            SecurityEvent.EventType.UNUSUAL_LOCATION;

            alertService.recordSecurityEvent(
                    eventType,
                    "Client risk level increased to " + profile.getRiskLevel() +
                            " (score: " + String.format("%.1f", profile.getRiskScore()) + ")",
                    Map.of(
                            "clientId", clientId,
                            "riskScore", String.format("%.1f", profile.getRiskScore()),
                            "riskLevel", profile.getRiskLevel().name(),
                            "previousLevel", previousLevel.name()
                    )
            );
        }
    }

    private void checkAndApplyDowngrade(String clientId, ClientRiskProfile profile) {
        if (profile.getRiskScore() >= criticalRiskThreshold) {
            applyDowngrade(clientId, profile, ClientRiskProfile.RiskLevel.CRITICAL,
                    "Critical risk threshold exceeded");
        } else if (profile.getRiskScore() >= highRiskThreshold) {
            applyDowngrade(clientId, profile, ClientRiskProfile.RiskLevel.HIGH,
                    "High risk threshold exceeded");
        }
    }

    private void applyDowngrade(String clientId, ClientRiskProfile profile,
                                 ClientRiskProfile.RiskLevel level, String reason) {
        if (!profile.isDowngradeActive() || profile.getRiskLevel().compareTo(level) > 0) {
            profile.setDowngradeUntil(Instant.now().plus(Duration.ofMinutes(downgradeDurationMinutes)));
            profile.setDowngradeReason(reason);

            log.warn("Applied downgrade to client {}: {} - action: {}, duration: {} minutes",
                    clientId, reason, profile.getCurrentDowngradeAction(),
                    downgradeDurationMinutes);

            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
                    String.format("Client downgraded: %s (action: %s)", reason, profile.getCurrentDowngradeAction()),
                    Map.of(
                            "clientId", clientId,
                            "riskScore", String.format("%.1f", profile.getRiskScore()),
                            "riskLevel", level.name(),
                            "downgradeAction", profile.getCurrentDowngradeAction().name(),
                            "reason", reason
                    )
            );
        }
    }

    public ClientRiskProfile.RiskLevel getClientRiskLevel(String clientId) {
        return getOrCreateProfile(clientId).getRiskLevel();
    }

    public double getClientRiskScore(String clientId) {
        return getOrCreateProfile(clientId).getRiskScore();
    }

    public boolean isClientDowngraded(String clientId) {
        return getOrCreateProfile(clientId).isDowngradeActive();
    }

    public ClientRiskProfile.DowngradeAction getClientDowngradeAction(String clientId) {
        return getOrCreateProfile(clientId).getCurrentDowngradeAction();
    }

    public boolean isClientBlocked(String clientId) {
        ClientRiskProfile profile = riskProfiles.get(clientId);
        if (profile == null) return false;
        return profile.getRiskLevel() == ClientRiskProfile.RiskLevel.BLOCKED ||
                (profile.isDowngradeActive() &&
                        profile.getCurrentDowngradeAction() == ClientRiskProfile.DowngradeAction.BLOCK);
    }

    public boolean shouldThrottleRequest(String clientId) {
        ClientRiskProfile profile = riskProfiles.get(clientId);
        if (profile == null || !profile.isDowngradeActive()) return false;

        return switch (profile.getCurrentDowngradeAction()) {
            case THROTTLE, RESTRICT_SCOPES, BLOCK -> true;
            default -> false;
        };
    }

    public Set<String> getRestrictedScopes(String clientId, Set<String> requestedScopes) {
        ClientRiskProfile profile = riskProfiles.get(clientId);
        if (profile == null || !profile.isDowngradeActive()) return requestedScopes;

        if (profile.getCurrentDowngradeAction() == ClientRiskProfile.DowngradeAction.RESTRICT_SCOPES ||
                profile.getCurrentDowngradeAction() == ClientRiskProfile.DowngradeAction.BLOCK) {
            return requestedScopes.stream()
                    .filter(scope -> scope.equals("openid") || scope.equals("profile"))
                    .collect(Collectors.toSet());
        }
        return requestedScopes;
    }

    public List<ClientRiskProfile> getHighRiskClients() {
        return riskProfiles.values().stream()
                .filter(p -> p.getRiskLevel() == ClientRiskProfile.RiskLevel.HIGH ||
                        p.getRiskLevel() == ClientRiskProfile.RiskLevel.CRITICAL ||
                        p.getRiskLevel() == ClientRiskProfile.RiskLevel.BLOCKED)
                .collect(Collectors.toList());
    }

    public List<ClientRiskProfile> getDowngradedClients() {
        return riskProfiles.values().stream()
                .filter(ClientRiskProfile::isDowngradeActive)
                .collect(Collectors.toList());
    }

    public Map<String, ClientRiskProfile> getAllRiskProfiles() {
        return new HashMap<>(riskProfiles);
    }

    public void releaseClientDowngrade(String clientId) {
        ClientRiskProfile profile = riskProfiles.get(clientId);
        if (profile != null) {
            profile.setDowngradeUntil(null);
            profile.setDowngradeReason(null);
            log.info("Released downgrade for client: {}", clientId);
        }
    }

    public void resetClientRisk(String clientId) {
        ClientRiskProfile profile = riskProfiles.get(clientId);
        if (profile != null) {
            profile.resetDailyCounters();
            profile.calculateRiskScore();
            profile.setDowngradeUntil(null);
            profile.setDowngradeReason(null);
            log.info("Reset risk profile for client: {}", clientId);
        }
    }

    @Scheduled(cron = "0 0 0 * * ?")
    public void resetDailyMetrics() {
        log.info("Resetting daily risk metrics for {} clients", riskProfiles.size());
        riskProfiles.values().forEach(ClientRiskProfile::resetDailyCounters);
    }
}

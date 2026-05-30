package com.sessionguard.service;

import com.sessionguard.collector.SessionProfileCollector;
import com.sessionguard.config.SessionGuardProperties;
import com.sessionguard.engine.RiskScoringEngine;
import com.sessionguard.ml.IsolationForestDetector;
import com.sessionguard.model.*;
import com.sessionguard.store.SessionStore;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class SessionGuardService {

    private final SessionStore sessionStore;
    private final SessionProfileCollector profileCollector;
    private final RiskScoringEngine riskScoringEngine;
    private final IsolationForestDetector mlDetector;
    private final WebhookNotificationService webhookService;
    private final SessionGuardProperties properties;
    private final ThreatIntelService threatIntelService;
    private final LocationJumpDetectionService locationJumpService;
    private final BehaviorLearningService behaviorLearningService;

    public SessionProfile createSession(HttpServletRequest request, String userId) {
        SessionProfile profile = profileCollector.collectNewSession(request, userId);

        int concurrentCount = sessionStore.getActiveSessionCount(userId);
        if (concurrentCount > 0) {
            log.info("User {} has {} existing sessions", userId, concurrentCount);
        }

        sessionStore.saveSession(profile, 120);

        sessionStore.saveIpHistory(userId, profile.getIpContext().getIpAddress());
        if (profile.getDeviceFingerprint() != null) {
            sessionStore.saveFingerprintHistory(userId, profile.getDeviceFingerprint().getFingerprintHash());
        }

        if (profile.getIpContext() != null) {
            sessionStore.saveUserLocation(userId,
                    profile.getIpContext().getGeoCountry(),
                    profile.getIpContext().getGeoRegion(),
                    profile.getIpContext().getGeoCity(),
                    profile.getIpContext().getIpAddress());
        }

        SessionEvent event = SessionEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .sessionId(profile.getSessionId())
                .userId(userId)
                .eventType(SessionEvent.EventType.SESSION_CREATED)
                .description("Session created from IP: " + profile.getIpContext().getIpAddress())
                .ipContext(profile.getIpContext())
                .deviceFingerprint(profile.getDeviceFingerprint())
                .timestamp(LocalDateTime.now())
                .riskScoreAtEvent(0)
                .build();
        sessionStore.logEvent(event);

        behaviorLearningService.updateBehaviorBaseline(userId, profile);

        log.info("Session created: {} for user: {}", profile.getSessionId(), userId);
        return profile;
    }

    public RiskAssessment verifySession(String sessionId, HttpServletRequest request) {
        return verifySession(sessionId, request, properties.getDefaultBusinessScenario());
    }

    public RiskAssessment verifySession(String sessionId, HttpServletRequest request, String businessScenario) {
        String effectiveScenario = businessScenario != null ? businessScenario : properties.getDefaultBusinessScenario();

        Optional<SessionProfile> existingOpt = sessionStore.getSession(sessionId);
        if (existingOpt.isEmpty()) {
            RiskAssessment assessment = createUnknownSessionAssessment(sessionId, effectiveScenario);
            return assessment;
        }

        SessionProfile existing = existingOpt.get();
        if (!existing.isActive()) {
            return createInvalidatedSessionAssessment(existing, effectiveScenario);
        }

        SessionProfile updated = profileCollector.updateFromRequest(existing, request);

        String currentIp = updated.getIpContext() != null ? updated.getIpContext().getIpAddress() : "unknown";
        ThreatIntel threat = threatIntelService.checkIpThreat(currentIp);
        LocationJumpDetection locationJump = locationJumpService.detectLocationJump(updated.getUserId(), updated);
        BehaviorLearningService.BaselineDeviationScore baselineDeviation = behaviorLearningService.calculateDeviation(updated.getUserId(), updated);

        RiskAssessment assessment = riskScoringEngine.assess(updated, existing, effectiveScenario);

        assessment = enrichWithMlAnalysis(updated, assessment, effectiveScenario);

        assessment = enrichWithThreatIntel(assessment, threat);
        assessment = enrichWithLocationJump(assessment, locationJump);
        assessment = enrichWithBaselineDeviation(assessment, baselineDeviation);

        int concurrentCount = sessionStore.getActiveSessionCount(updated.getUserId());
        if (concurrentCount > 1) {
            int concurrentScore = riskScoringEngine.assessConcurrentSessionRisk(concurrentCount, effectiveScenario);
            if (concurrentScore > 0) {
                assessment.getRiskFactors().add(RiskFactor.builder()
                        .category("SESSION")
                        .name("CONCURRENT_SESSIONS")
                        .description(concurrentCount + " concurrent sessions detected")
                        .weight(properties.getRiskWeights().getConcurrentSession())
                        .score(concurrentScore)
                        .detail("Active sessions: " + concurrentCount)
                        .build());
                assessment.setTotalScore(Math.min(assessment.getTotalScore() + concurrentScore, 100));
            }
        }

        assessment.setBusinessScenario(effectiveScenario);
        assessment.setUserGuidance(buildUserGuidance(assessment, effectiveScenario));

        Map<String, Object> extendedInfo = new HashMap<>();
        if (threat != null) {
            extendedInfo.put("threatIntel", Map.of(
                    "type", threat.getThreatType(),
                    "severity", threat.getSeverity(),
                    "source", threat.getSource()
            ));
        }
        if (locationJump != null && locationJump.getJumpLevel().getLevel() > 0) {
            extendedInfo.put("locationJump", Map.of(
                    "level", locationJump.getJumpLevel(),
                    "description", locationJump.getDescription()
            ));
        }
        if (!baselineDeviation.deviations().isEmpty()) {
            extendedInfo.put("baselineDeviations", baselineDeviation.deviations());
        }
        assessment.setExtendedDetectionInfo(extendedInfo);

        sessionStore.saveSession(updated, 120);
        sessionStore.saveRiskAssessment(assessment, 120);

        logEventsFromAssessment(updated, existing, assessment);

        sessionStore.saveIpHistory(updated.getUserId(), updated.getIpContext().getIpAddress());
        if (updated.getDeviceFingerprint() != null) {
            sessionStore.saveFingerprintHistory(updated.getUserId(), updated.getDeviceFingerprint().getFingerprintHash());
        }
        if (updated.getIpContext() != null) {
            sessionStore.saveUserLocation(updated.getUserId(),
                    updated.getIpContext().getGeoCountry(),
                    updated.getIpContext().getGeoRegion(),
                    updated.getIpContext().getGeoCity(),
                    updated.getIpContext().getIpAddress());
        }

        behaviorLearningService.updateBehaviorBaseline(updated.getUserId(), updated);

        if (assessment.getRiskLevel() == RiskAssessment.RiskLevel.HIGH
                || assessment.getRiskLevel() == RiskAssessment.RiskLevel.CRITICAL) {
            webhookService.sendAlert(buildWebhookPayload(updated, assessment));
        }

        log.info("Session {} verified (scenario: {}): risk={}, level={}, threat={}, jump={}",
                sessionId, effectiveScenario, assessment.getTotalScore(), assessment.getRiskLevel(),
                threat != null ? threat.getThreatType() : "none",
                locationJump != null ? locationJump.getJumpLevel() : "none");
        return assessment;
    }

    public void invalidateSession(String sessionId, String reason) {
        sessionStore.invalidateSession(sessionId, reason);

        SessionEvent event = SessionEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .sessionId(sessionId)
                .eventType(SessionEvent.EventType.SESSION_INVALIDATED)
                .description("Session invalidated: " + reason)
                .timestamp(LocalDateTime.now())
                .riskScoreAtEvent(100)
                .build();
        sessionStore.logEvent(event);

        log.warn("Session {} forcibly invalidated: {}", sessionId, reason);
    }

    public void invalidateAllUserSessions(String userId, String reason) {
        sessionStore.invalidateAllUserSessions(userId, reason);
        log.warn("All sessions for user {} forcibly invalidated: {}", userId, reason);
    }

    public Optional<SessionProfile> getSession(String sessionId) {
        return sessionStore.getSession(sessionId);
    }

    public List<SessionProfile> getUserSessions(String userId) {
        return sessionStore.getSessionsByUser(userId);
    }

    public Optional<RiskAssessment> getRiskAssessment(String sessionId) {
        return sessionStore.getLatestRiskAssessment(sessionId);
    }

    public List<SessionEvent> getSessionHistory(String sessionId) {
        return sessionStore.getEventHistory(sessionId);
    }

    public void trainModel() {
        List<SessionProfile> allProfiles = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            SessionProfile synthetic = createSyntheticProfile("train-user-" + i, false);
            allProfiles.add(synthetic);
        }
        for (int i = 0; i < 5; i++) {
            SessionProfile anomalous = createSyntheticProfile("anomaly-user-" + i, true);
            allProfiles.add(anomalous);
        }

        mlDetector.train(allProfiles);
        log.info("ML model training completed with {} samples", allProfiles.size());
    }

    private RiskAssessment enrichWithMlAnalysis(SessionProfile profile, RiskAssessment assessment, String businessScenario) {
        if (mlDetector.isTrained()) {
            IsolationForestDetector.AnomalyResult mlResult = mlDetector.detectAnomaly(profile);

            Map<String, Object> mlInfo = new HashMap<>();
            mlInfo.put("anomalyScore", mlResult.anomalyScore());
            mlInfo.put("isAnomaly", mlResult.isAnomaly());
            mlInfo.put("message", mlResult.message());
            assessment.setMlAnomalyResult(mlInfo);

            if (mlResult.isAnomaly()) {
                int mlScore = (int) (mlResult.anomalyScore() * properties.getRiskWeights().getMlAnomaly());
                assessment.getRiskFactors().add(RiskFactor.builder()
                        .category("ML")
                        .name("ML_ANOMALY_DETECTED")
                        .description("Machine learning detected anomaly: " + mlResult.message())
                        .weight(properties.getRiskWeights().getMlAnomaly())
                        .score(mlScore)
                        .detail("Anomaly score: " + String.format("%.4f", mlResult.anomalyScore()))
                        .build());
                assessment.setTotalScore(Math.min(assessment.getTotalScore() + mlScore, 100));
            }
        }
        return assessment;
    }

    private RiskAssessment enrichWithThreatIntel(RiskAssessment assessment, ThreatIntel threat) {
        if (threat != null && threat.isActive()) {
            int threatScore = threat.getSeverity().getBaseScore();
            String detail = String.format("IP flagged as %s (source: %s, hits: %d",
                    threat.getThreatType(), threat.getSource(), threat.getHitCount());

            assessment.getRiskFactors().add(RiskFactor.builder()
                    .category("THREAT")
                    .name("KNOWN_THREAT_IP")
                    .description("Known threat IP detected: " + threat.getDescription())
                    .weight(threatScore)
                    .score(threatScore)
                    .detail(detail)
                    .build());
            assessment.setTotalScore(Math.min(assessment.getTotalScore() + threatScore, 100));
        }
        return assessment;
    }

    private RiskAssessment enrichWithLocationJump(RiskAssessment assessment, LocationJumpDetection jump) {
        if (jump != null && jump.getRiskScoreContribution() > 0) {
            assessment.getRiskFactors().add(RiskFactor.builder()
                    .category("LOCATION")
                    .name("LOCATION_JUMP_DETECTED")
                    .description(jump.getDescription())
                    .weight(jump.getRiskScoreContribution())
                    .score(jump.getRiskScoreContribution())
                    .detail(String.format("Speed: %.0f km/h, Distance: %.0f km, Gap: %d min",
                            jump.getCalculatedSpeedKmh(), jump.getDistanceKm(), jump.getTimeGapMinutes()))
                    .build());
            assessment.setTotalScore(Math.min(assessment.getTotalScore() + jump.getRiskScoreContribution(), 100));
        }
        return assessment;
    }

    private RiskAssessment enrichWithBaselineDeviation(RiskAssessment assessment, BehaviorLearningService.BaselineDeviationScore deviation) {
        if (deviation.totalScore() > 0) {
            assessment.getRiskFactors().add(RiskFactor.builder()
                    .category("BASELINE")
                    .name("BEHAVIOR_DEVIATION")
                    .description("Behavior deviates from user's normal pattern")
                    .weight(deviation.totalScore())
                    .score(deviation.totalScore())
                    .detail("Deviations: " + String.join("; ", deviation.deviations()))
                    .build());
            assessment.setTotalScore(Math.min(assessment.getTotalScore() + deviation.totalScore(), 100));
        }
        return assessment;
    }

    private RiskAssessment.UserGuidance buildUserGuidance(RiskAssessment assessment, String businessScenario) {
        SessionGuardProperties.BusinessScenarioConfig scenarioConfig = properties.getScenarioConfig(businessScenario);
        SessionGuardProperties.UserGuidanceConfig guidanceConfig = properties.getUserGuidance();

        String friendlyMessage = buildFriendlyMessage(assessment, scenarioConfig);

        return RiskAssessment.UserGuidance.builder()
                .friendlyMessage(friendlyMessage)
                .reauthUrl(guidanceConfig.getReauthUrl())
                .supportContact(guidanceConfig.getSupportContact())
                .maxReauthAttempts(guidanceConfig.getMaxReauthAttempts())
                .reauthCooldownMinutes(guidanceConfig.getReauthCooldownMinutes())
                .build();
    }

    private String buildFriendlyMessage(RiskAssessment assessment, SessionGuardProperties.BusinessScenarioConfig scenarioConfig) {
        if (assessment.getRiskLevel() == RiskAssessment.RiskLevel.LOW
                || assessment.getRiskLevel() == RiskAssessment.RiskLevel.MEDIUM) {
            return "您的会话状态正常，欢迎继续使用";
        }

        if (scenarioConfig.getFriendlyMessage() != null) {
            return scenarioConfig.getFriendlyMessage();
        }

        return switch (assessment.getRiskLevel()) {
            case HIGH -> "检测到会话存在安全风险，请重新登录以确保账户安全";
            case CRITICAL -> "会话已失效，为保障您的账户安全，请立即重新登录";
            default -> "会话验证成功";
        };
    }

    private void logEventsFromAssessment(SessionProfile current, SessionProfile previous, RiskAssessment assessment) {
        for (RiskFactor factor : assessment.getRiskFactors()) {
            SessionEvent.EventType eventType = mapToEventType(factor.getName());
            SessionEvent event = SessionEvent.builder()
                    .eventId(UUID.randomUUID().toString())
                    .sessionId(current.getSessionId())
                    .userId(current.getUserId())
                    .eventType(eventType)
                    .description(factor.getDescription())
                    .ipContext(current.getIpContext())
                    .deviceFingerprint(current.getDeviceFingerprint())
                    .timestamp(LocalDateTime.now())
                    .riskScoreAtEvent(assessment.getTotalScore())
                    .build();
            sessionStore.logEvent(event);
        }
    }

    private SessionEvent.EventType mapToEventType(String factorName) {
        return switch (factorName) {
            case "IP_ADDRESS_CHANGED", "SUBNET_CHANGED" -> SessionEvent.EventType.IP_CHANGED;
            case "COUNTRY_CHANGED", "REGION_CHANGED" -> SessionEvent.EventType.IP_CHANGED;
            case "DEVICE_FINGERPRINT_CHANGED", "USER_AGENT_CHANGED" -> SessionEvent.EventType.FINGERPRINT_CHANGED;
            case "COOKIE_ID_CHANGED" -> SessionEvent.EventType.COOKIE_ANOMALY;
            case "ML_ANOMALY_DETECTED" -> SessionEvent.EventType.ML_ANOMALY_DETECTED;
            case "CONCURRENT_SESSIONS" -> SessionEvent.EventType.CONCURRENT_SESSION_DETECTED;
            case "KNOWN_THREAT_IP" -> SessionEvent.EventType.THREAT_DETECTED;
            case "LOCATION_JUMP_DETECTED" -> SessionEvent.EventType.LOCATION_JUMP_DETECTED;
            default -> SessionEvent.EventType.RISK_SCORE_UPDATED;
        };
    }

    private WebhookPayload buildWebhookPayload(SessionProfile profile, RiskAssessment assessment) {
        Map<String, Object> details = new HashMap<>();
        details.put("riskFactors", assessment.getRiskFactors().stream()
                .map(RiskFactor::getName).toList());
        details.put("recommendedAction", assessment.getRecommendedAction());
        details.put("businessScenario", assessment.getBusinessScenario());
        if (assessment.getMlAnomalyResult() != null) {
            details.put("mlResult", assessment.getMlAnomalyResult());
        }
        if (assessment.getUserGuidance() != null) {
            details.put("friendlyMessage", assessment.getUserGuidance().getFriendlyMessage());
        }
        if (assessment.getExtendedDetectionInfo() != null) {
            details.putAll(assessment.getExtendedDetectionInfo());
        }

        return WebhookPayload.builder()
                .alertId(UUID.randomUUID().toString())
                .sessionId(profile.getSessionId())
                .userId(profile.getUserId())
                .riskLevel(assessment.getRiskLevel())
                .riskScore(assessment.getTotalScore())
                .alertType("SESSION_HIJACKING_RISK")
                .message("High risk session detected for user " + profile.getUserId())
                .details(details)
                .timestamp(LocalDateTime.now())
                .build();
    }

    private RiskAssessment createUnknownSessionAssessment(String sessionId, String businessScenario) {
        SessionGuardProperties.BusinessScenarioConfig scenarioConfig = properties.getScenarioConfig(businessScenario);

        RiskAssessment assessment = RiskAssessment.builder()
                .sessionId(sessionId)
                .totalScore(100)
                .riskLevel(RiskAssessment.RiskLevel.CRITICAL)
                .riskFactors(List.of(RiskFactor.builder()
                        .category("SESSION")
                        .name("SESSION_NOT_FOUND")
                        .description("Session does not exist")
                        .weight(100)
                        .score(100)
                        .build()))
                .assessedAt(LocalDateTime.now())
                .requiresAction(true)
                .recommendedAction("INVALIDATE_SESSION_IMMEDIATELY")
                .businessScenario(businessScenario)
                .build());

        assessment.setUserGuidance(buildUserGuidance(assessment, businessScenario));
        return assessment;
    }

    private RiskAssessment createInvalidatedSessionAssessment(SessionProfile profile, String businessScenario) {
        RiskAssessment assessment = RiskAssessment.builder()
                .sessionId(profile.getSessionId())
                .userId(profile.getUserId())
                .totalScore(100)
                .riskLevel(RiskAssessment.RiskLevel.CRITICAL)
                .riskFactors(List.of(RiskFactor.builder()
                        .category("SESSION")
                        .name("SESSION_ALREADY_INVALIDATED")
                        .description("Session has been invalidated: " + profile.getInvalidationReason())
                        .weight(100)
                        .score(100)
                        .detail("Reason: " + profile.getInvalidationReason())
                        .build()))
                .assessedAt(LocalDateTime.now())
                .requiresAction(true)
                .recommendedAction("REJECT_REQUEST")
                .businessScenario(businessScenario)
                .build());

        assessment.setUserGuidance(buildUserGuidance(assessment, businessScenario));
        return assessment;
    }

    private SessionProfile createSyntheticProfile(String userId, boolean anomalous) {
        Random r = new Random();
        String ip = anomalous ? r.nextInt(256) + "." + r.nextInt(256) + "." + r.nextInt(256) + "." + r.nextInt(256)
                : "192.168.1." + r.nextInt(255);

        return SessionProfile.builder()
                .sessionId(UUID.randomUUID().toString())
                .userId(userId)
                .cookieId(UUID.randomUUID().toString())
                .ipContext(IpContext.builder()
                        .ipAddress(ip)
                        .subnetPrefix("192.168.1.0/24")
                        .geoCountry(anomalous ? "FOREIGN" : "CN")
                        .geoCity(anomalous ? "Foreign" : "Beijing")
                        .geoRegion(anomalous ? "Alien" : "BJ")
                        .isp("ISP")
                        .isProxy(anomalous && r.nextBoolean())
                        .isVpn(anomalous && r.nextBoolean())
                        .isTor(anomalous && r.nextBoolean())
                        .isDataCenter(false)
                        .build())
                .deviceFingerprint(DeviceFingerprint.builder()
                        .fingerprintHash(UUID.randomUUID().toString())
                        .userAgent(anomalous ? "SuspiciousBot/1.0" : "Mozilla/5.0 Chrome/120")
                        .platform(anomalous ? "Unknown" : "Windows")
                        .browser(anomalous ? "Unknown" : "Chrome")
                        .browserVersion("120")
                        .os(anomalous ? "Unknown" : "Windows")
                        .osVersion("10")
                        .screenResolution("1920x1080")
                        .timezone("Asia/Shanghai")
                        .language("zh_CN")
                        .build())
                .createdAt(LocalDateTime.now().minusMinutes(r.nextInt(120)))
                .lastAccessedAt(LocalDateTime.now())
                .lastVerifiedAt(LocalDateTime.now())
                .accessCount(r.nextInt(50) + 1)
                .active(true)
                .invalidated(false)
                .build();
    }
}

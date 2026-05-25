package com.riskcontrol.service;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.enums.RiskLevel;
import com.riskcontrol.common.model.*;
import com.riskcontrol.common.utils.GeolocationUtil;
import com.riskcontrol.flink.source.RiskEventSource;
import com.riskcontrol.ml.engine.MLScoringService;
import com.riskcontrol.redis.service.*;
import com.riskcontrol.rules.engine.RuleEngineService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class RiskAssessmentService {

    private static final Logger logger = LoggerFactory.getLogger(RiskAssessmentService.class);

    private final RuleEngineService ruleEngineService;
    private final MLScoringService mlScoringService;
    private final EventPreprocessingService preprocessingService;
    private final DeviceFingerprintService deviceFingerprintService;
    private final IpBlacklistService ipBlacklistService;
    private final UserBehaviorService userBehaviorService;
    private final RateLimitingService rateLimitingService;
    private final RiskEventSource riskEventSource;
    private final DecisionExplanationService explanationService;
    private final RiskDashboardService dashboardService;

    @Value("${riskcontrol.ml.enabled:true}")
    private boolean mlEnabled;

    @Value("${riskcontrol.flink.enabled:true}")
    private boolean flinkEnabled;

    @Autowired
    public RiskAssessmentService(RuleEngineService ruleEngineService,
                                 MLScoringService mlScoringService,
                                 EventPreprocessingService preprocessingService,
                                 DeviceFingerprintService deviceFingerprintService,
                                 IpBlacklistService ipBlacklistService,
                                 UserBehaviorService userBehaviorService,
                                 RateLimitingService rateLimitingService,
                                 RiskEventSource riskEventSource,
                                 DecisionExplanationService explanationService,
                                 RiskDashboardService dashboardService) {
        this.ruleEngineService = ruleEngineService;
        this.mlScoringService = mlScoringService;
        this.preprocessingService = preprocessingService;
        this.deviceFingerprintService = deviceFingerprintService;
        this.ipBlacklistService = ipBlacklistService;
        this.userBehaviorService = userBehaviorService;
        this.rateLimitingService = rateLimitingService;
        this.riskEventSource = riskEventSource;
        this.explanationService = explanationService;
        this.dashboardService = dashboardService;
    }

    public RiskAssessmentResult assessLoginRisk(RiskEvent event) {
        event.setEventType(EventType.LOGIN);
        return assessRisk(event);
    }

    public RiskAssessmentResult assessRegisterRisk(RiskEvent event) {
        event.setEventType(EventType.REGISTER);
        return assessRisk(event);
    }

    public RiskAssessmentResult assessPasswordChangeRisk(RiskEvent event) {
        event.setEventType(EventType.PASSWORD_CHANGE);
        return assessRisk(event);
    }

    public RiskAssessmentResult assessRisk(RiskEvent event) {
        long startTime = System.currentTimeMillis();

        if (event.getEventId() == null || event.getEventId().isEmpty()) {
            event.setEventId(UUID.randomUUID().toString());
        }
        if (event.getEventTimestamp() == 0) {
            event.setEventTimestamp(System.currentTimeMillis());
        }

        logger.info("Starting risk assessment for event: {}, type: {}",
                event.getEventId(), event.getEventType());

        preprocessingService.preprocessEvent(event);
        enrichEventWithContext(event);
        calculateVelocity(event);

        if (!checkRateLimit(event)) {
            return createRateLimitResult(event);
        }

        RiskAssessmentResult result = ruleEngineService.evaluateRules(event);
        FeatureVector features = null;
        UserBehaviorProfile profile = null;

        if (mlEnabled) {
            profile = userBehaviorService.getUserBehaviorProfile(event.getUserId());
            result = mlScoringService.scoreWithML(event, profile, result);
            try {
                features = mlScoringService.buildFeaturesForExplanation(event, profile);
            } catch (Exception e) {
                logger.debug("Could not build features for explanation", e);
            }
        }

        RiskLevel finalLevel = RiskLevel.fromScore(result.getFinalScore());
        result.setRiskLevel(finalLevel);
        result.setIsAllowed(result.getFinalScore() < 90);

        DecisionExplanation explanation = explanationService.generateExplanation(event, result, profile, features);
        result.setExplanation(explanation);

        try {
            dashboardService.recordEvent(event, result);
        } catch (Exception e) {
            logger.debug("Could not record event to dashboard", e);
        }

        if (result.getFinalScore() >= 70) {
            result.setRequireMfa(true);
        }
        if (result.getFinalScore() >= 85) {
            result.setBlockAccount(true);
            result.setIsAllowed(false);
        }

        long processingTime = System.currentTimeMillis() - startTime;
        result.setProcessingTimeMs(processingTime);
        result.setAssessmentTimestamp(System.currentTimeMillis());

        postAssessmentProcessing(event, result);

        if (flinkEnabled) {
            riskEventSource.sendRiskEvent(event);
        }

        logger.info("Risk assessment completed for event {}: score={}, level={}, allowed={}",
                event.getEventId(), result.getFinalScore(), result.getRiskLevel(), result.isAllowed());

        return result;
    }

    private void enrichEventWithContext(RiskEvent event) {
        String userId = event.getUserId();

        if (userId != null) {
            event.setLastLoginTimestamp(userBehaviorService.getLastLoginTimestamp(userId));
            event.setLastLoginIp(userBehaviorService.getLastLoginIp(userId));
            event.setLastLoginDeviceId(userBehaviorService.getLastLoginDeviceId(userId));
            event.setLoginAttemptCount(userBehaviorService.getFailedLoginAttempts(userId, event.getIpAddress()));
        }

        if (event.getDeviceFingerprint() != null) {
            DeviceFingerprint savedFingerprint = deviceFingerprintService
                    .saveDeviceFingerprint(event.getDeviceFingerprint());
            event.setDeviceFingerprint(savedFingerprint);
        }

        if (event.getIpInfo() == null && event.getIpAddress() != null) {
            IpInfo ipInfo = ipBlacklistService.getIpInfo(event.getIpAddress());
            if (ipInfo != null) {
                event.setIpInfo(ipInfo);
            } else {
                event.setIpInfo(IpInfo.builder()
                        .ipAddress(event.getIpAddress())
                        .isBlacklisted(ipBlacklistService.isBlacklisted(event.getIpAddress()))
                        .riskScore(ipBlacklistService.getIpRiskScore(event.getIpAddress()))
                        .build());
            }
        }

        if (event.getIpInfo() != null) {
            event.getIpInfo().setBlacklisted(ipBlacklistService.isBlacklisted(event.getIpAddress()));
        }

        if (event.getDeviceFingerprint() != null && event.getDeviceFingerprint().getDeviceId() != null) {
            int associationCount = deviceFingerprintService
                    .getDeviceAssociationCount(event.getDeviceFingerprint().getDeviceId());
            event.getDeviceFingerprint().setAssociationCount(associationCount);
        }
    }

    private void calculateVelocity(RiskEvent event) {
        if (event.getIpInfo() == null || event.getLastLoginIp() == null) {
            return;
        }

        IpInfo currentIpInfo = event.getIpInfo();
        IpInfo lastIpInfo = ipBlacklistService.getIpInfo(event.getLastLoginIp());

        if (lastIpInfo != null && event.getLastLoginTimestamp() > 0) {
            double velocity = GeolocationUtil.calculateVelocityKmPerHour(
                    lastIpInfo.getLatitude(), lastIpInfo.getLongitude(), event.getLastLoginTimestamp(),
                    currentIpInfo.getLatitude(), currentIpInfo.getLongitude(), event.getEventTimestamp()
            );
            event.setVelocityKmPerHour(velocity);
            logger.debug("Calculated velocity for user {}: {} km/h", event.getUserId(), velocity);
        }
    }

    private boolean checkRateLimit(RiskEvent event) {
        String ip = event.getIpAddress();
        String account = event.getAccount() != null ? event.getAccount() : event.getUserId();

        if (event.getEventType() == EventType.LOGIN) {
            if (!rateLimitingService.tryAcquireLogin(ip)) {
                logger.warn("Login rate limit exceeded for IP: {}", ip);
                return false;
            }
            if (account != null && !rateLimitingService.tryAcquireLoginPerAccount(account)) {
                logger.warn("Login rate limit exceeded for account: {}", account);
                return false;
            }
        } else if (event.getEventType() == EventType.REGISTER) {
            if (!rateLimitingService.tryAcquireRegister(ip)) {
                logger.warn("Register rate limit exceeded for IP: {}", ip);
                return false;
            }
        } else if (event.getEventType() == EventType.PASSWORD_CHANGE) {
            if (event.getUserId() != null && !rateLimitingService.tryAcquirePasswordChange(event.getUserId())) {
                logger.warn("Password change rate limit exceeded for user: {}", event.getUserId());
                return false;
            }
        }

        return true;
    }

    private RiskAssessmentResult createRateLimitResult(RiskEvent event) {
        return RiskAssessmentResult.builder()
                .eventId(event.getEventId())
                .userId(event.getUserId())
                .riskLevel(RiskLevel.HIGH)
                .ruleScore(80)
                .mlScore(0)
                .finalScore(80)
                .isAllowed(false)
                .requireCaptcha(true)
                .decisionReason("Rate limit exceeded")
                .assessmentTimestamp(System.currentTimeMillis())
                .processingTimeMs(System.currentTimeMillis() - event.getEventTimestamp())
                .build();
    }

    private void postAssessmentProcessing(RiskEvent event, RiskAssessmentResult result) {
        String userId = event.getUserId();
        String deviceId = event.getDeviceFingerprint() != null ?
                event.getDeviceFingerprint().getDeviceId() : null;
        String country = event.getIpInfo() != null ? event.getIpInfo().getCountry() : null;

        if (userId != null) {
            if (result.isAllowed() && event.getEventType() == EventType.LOGIN) {
                userBehaviorService.recordLogin(
                        userId, event.getIpAddress(), deviceId, country, event.getEventTimestamp()
                );
                userBehaviorService.resetFailedLoginAttempts(userId, event.getIpAddress());
            } else if (!result.isAllowed() && event.getEventType() == EventType.LOGIN) {
                userBehaviorService.recordFailedLogin(userId, event.getIpAddress());
            }

            if (result.getFinalScore() >= 70) {
                userBehaviorService.recordFraudFlag(userId, result.getDecisionReason());
            }

            if (event.getEventType() == EventType.REGISTER) {
                userBehaviorService.initializeUserProfile(userId);
            }

            if (event.getEventType() == EventType.PASSWORD_CHANGE) {
                userBehaviorService.recordPasswordChange(userId);
            }

            if (deviceId != null) {
                deviceFingerprintService.associateDeviceWithAccount(deviceId, userId);
            }
        }
    }
}

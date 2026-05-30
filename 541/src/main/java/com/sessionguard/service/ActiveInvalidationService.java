package com.sessionguard.service;

import com.sessionguard.config.SessionGuardProperties;
import com.sessionguard.model.RiskAssessment;
import com.sessionguard.model.SessionProfile;
import com.sessionguard.store.SessionStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class ActiveInvalidationService {

    private final SessionStore sessionStore;
    private final WebhookNotificationService webhookService;
    private final SessionGuardProperties properties;

    public InvalidationResult handleRiskAssessment(SessionProfile profile, RiskAssessment assessment, String businessScenario) {
        SessionGuardProperties.BusinessScenarioConfig scenarioConfig = properties.getScenarioConfig(businessScenario);

        if (!properties.isActiveInvalidationEnabled()) {
            return new InvalidationResult(false, "Active invalidation disabled");
        }

        if (assessment.getRiskLevel() == RiskAssessment.RiskLevel.CRITICAL
                && scenarioConfig.isAutoInvalidateOnCritical()) {
            String reason = "Auto-invalidated: critical risk detected (score: " + assessment.getTotalScore()
                    + ", scenario: " + businessScenario + ")";
            sessionStore.invalidateSession(profile.getSessionId(), reason);
            webhookService.sendSessionInvalidationAlert(profile, reason);

            log.warn("Session {} auto-invalidated due to critical risk (scenario: {}): score={}",
                    profile.getSessionId(), businessScenario, assessment.getTotalScore());
            return new InvalidationResult(true, reason, scenarioConfig.getFriendlyMessage());
        }

        if (assessment.getRiskLevel() == RiskAssessment.RiskLevel.HIGH
                && scenarioConfig.isRequireReauthOnHigh()) {
            log.warn("Session {} flagged as HIGH risk (scenario: {}, score={}) - requiring re-authentication",
                    profile.getSessionId(), businessScenario, assessment.getTotalScore());
            return new InvalidationResult(false, "Re-authentication required", scenarioConfig.getFriendlyMessage());
        }

        return new InvalidationResult(false, "No action required", null);
    }

    public InvalidationResult handleRiskAssessment(SessionProfile profile, RiskAssessment assessment) {
        return handleRiskAssessment(profile, assessment, properties.getDefaultBusinessScenario());
    }

    public InvalidationResult forceInvalidate(String sessionId, String reason) {
        if (!properties.isActiveInvalidationEnabled()) {
            return new InvalidationResult(false, "Active invalidation disabled", null);
        }

        sessionStore.invalidateSession(sessionId, reason);

        sessionStore.getSession(sessionId).ifPresent(profile -> {
            webhookService.sendSessionInvalidationAlert(profile, reason);
        });

        log.info("Session {} forcibly invalidated: {}", sessionId, reason);
        return new InvalidationResult(true, "Session invalidated: " + reason,
                "为保障您的账户安全，本次会话已终止，请重新登录");
    }

    public InvalidationResult forceInvalidateAllUserSessions(String userId, String reason) {
        if (!properties.isActiveInvalidationEnabled()) {
            return new InvalidationResult(false, "Active invalidation disabled", null);
        }

        sessionStore.invalidateAllUserSessions(userId, reason);
        log.info("All sessions for user {} forcibly invalidated: {}", userId, reason);
        return new InvalidationResult(true, "All user sessions invalidated: " + reason,
                "检测到账户异常，为保障您的账户安全，已终止所有登录会话，请重新登录");
    }

    public boolean checkConcurrentSessionLimit(String userId) {
        int count = sessionStore.getActiveSessionCount(userId);
        if (count > properties.getSession().getMaxConcurrentSessions()) {
            log.warn("User {} exceeds concurrent session limit: {}/{}",
                    userId, count, properties.getSession().getMaxConcurrentSessions());
            return false;
        }
        return true;
    }

    public record InvalidationResult(boolean invalidated, String message, String friendlyMessage) {
        public InvalidationResult(boolean invalidated, String message) {
            this(invalidated, message, null);
        }
    }
}

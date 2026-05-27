package com.sso.session;

import com.sso.entity.UserSession;
import com.sso.repository.UserSessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@RequiredArgsConstructor
public class SynchronousLogoutHandler {

    private static final int SLO_TIMEOUT_SECONDS = 10;
    private static final int MAX_RETRIES = 2;

    private final UserSessionRepository userSessionRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final RestTemplate restTemplate = new RestTemplate();

    public LogoutResult performSynchronousLogout(String username, String sessionId) {
        log.info("Synchronous SLO initiated for user: {}, session: {}", username, sessionId);

        LogoutResult result = new LogoutResult();
        result.setUsername(username);
        result.setSessionId(sessionId);

        List<UserSession> activeSessions = userSessionRepository.findByUsernameAndActiveTrue(username);
        result.setTotalSubsystems(activeSessions.size());

        List<CompletableFuture<LogoutNotificationResult>> futures = new ArrayList<>();

        for (UserSession session : activeSessions) {
            if (session.getLogoutUrl() != null && !session.getLogoutUrl().isEmpty()) {
                CompletableFuture<LogoutNotificationResult> future = 
                        CompletableFuture.supplyAsync(() -> notifySubsystem(session));
                futures.add(future);
            }
        }

        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .orTimeout(SLO_TIMEOUT_SECONDS, TimeUnit.SECONDS)
                .join();

        int successCount = 0;
        int failureCount = 0;
        List<String> failures = new ArrayList<>();

        for (CompletableFuture<LogoutNotificationResult> future : futures) {
            try {
                LogoutNotificationResult notificationResult = future.get();
                if (notificationResult.isSuccess()) {
                    successCount++;
                    result.getSuccessNotifications().add(notificationResult);
                } else {
                    failureCount++;
                    result.getFailureNotifications().add(notificationResult);
                    failures.add(notificationResult.getSessionId() + ": " + notificationResult.getErrorMessage());
                }
            } catch (Exception e) {
                failureCount++;
                log.error("Error getting notification result", e);
            }
        }

        result.setSuccessCount(successCount);
        result.setFailureCount(failureCount);
        result.setAllSuccess(failureCount == 0);

        invalidateLocalSession(sessionId);
        invalidateAllUserSessions(username);
        cleanupRedisSessions(username);

        if (result.isAllSuccess()) {
            log.info("Synchronous SLO completed successfully for user: {}, all {} subsystems notified", 
                    username, successCount);
        } else {
            log.warn("Synchronous SLO completed with failures for user: {}, success: {}, failed: {}", 
                    username, successCount, failureCount);
            log.warn("Failed subsystems: {}", failures);
        }

        result.setCompletedAt(LocalDateTime.now());
        return result;
    }

    private LogoutNotificationResult notifySubsystem(UserSession session) {
        LogoutNotificationResult result = new LogoutNotificationResult();
        result.setSessionId(session.getSessionId());
        result.setSubsystemUrl(session.getLogoutUrl());
        result.setProtocol(session.getProtocol());

        for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                if (attempt > 0) {
                    log.debug("Retry attempt {} for session: {}", attempt, session.getSessionId());
                    Thread.sleep(1000L * attempt);
                }

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                headers.set("X-SSO-Logout", "true");
                headers.set("X-Session-Id", session.getSessionId());

                LogoutRequest request = new LogoutRequest();
                request.setSessionId(session.getSessionId());
                request.setUsername(session.getUsername());
                request.setProtocol(session.getProtocol());
                request.setTimestamp(LocalDateTime.now().toString());

                HttpEntity<LogoutRequest> entity = new HttpEntity<>(request, headers);

                ResponseEntity<String> response = restTemplate.postForEntity(
                        session.getLogoutUrl(), entity, String.class);

                if (response.getStatusCode().is2xxSuccessful()) {
                    result.setSuccess(true);
                    result.setResponseStatusCode(response.getStatusCode().value());
                    result.setAttempts(attempt + 1);
                    log.info("SLO notification success for session: {} (attempt {})", 
                            session.getSessionId(), attempt + 1);
                    return result;
                } else {
                    result.setErrorMessage("HTTP " + response.getStatusCode().value());
                    result.setResponseStatusCode(response.getStatusCode().value());
                }
            } catch (Exception e) {
                result.setErrorMessage(e.getMessage());
                log.warn("SLO notification failed for session: {} (attempt {}): {}", 
                        session.getSessionId(), attempt + 1, e.getMessage());
            }
        }

        result.setAttempts(MAX_RETRIES + 1);
        return result;
    }

    private void invalidateLocalSession(String sessionId) {
        userSessionRepository.invalidateSession(sessionId);
        log.debug("Invalidated local session: {}", sessionId);
    }

    private void invalidateAllUserSessions(String username) {
        List<UserSession> activeSessions = userSessionRepository.findByUsernameAndActiveTrue(username);
        for (UserSession userSession : activeSessions) {
            userSessionRepository.invalidateSession(userSession.getSessionId());
            log.debug("Invalidated session: {} for user: {}", userSession.getSessionId(), username);
        }
    }

    private void cleanupRedisSessions(String username) {
        try {
            String pattern = "sso:session:*";
            Set<String> keys = redisTemplate.keys(pattern);
            if (keys != null) {
                for (String key : keys) {
                    try {
                        Object sessionAttrs = redisTemplate.opsForHash()
                                .get(key, "sessionAttr:SPRING_SECURITY_CONTEXT");
                        if (sessionAttrs != null && sessionAttrs.toString().contains(username)) {
                            redisTemplate.delete(key);
                            log.debug("Deleted Redis session: {} for user: {}", key, username);
                        }
                    } catch (Exception e) {
                        log.warn("Failed to process Redis key: {}", key, e);
                    }
                }
            }

            String userSessionsKey = "sso:user:sessions:" + username;
            redisTemplate.delete(userSessionsKey);
        } catch (Exception e) {
            log.error("Failed to cleanup Redis sessions for user: {}", username, e);
        }
    }

    public static class LogoutResult {
        private String username;
        private String sessionId;
        private int totalSubsystems;
        private int successCount;
        private int failureCount;
        private boolean allSuccess;
        private LocalDateTime completedAt;
        private List<LogoutNotificationResult> successNotifications = new ArrayList<>();
        private List<LogoutNotificationResult> failureNotifications = new ArrayList<>();

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public int getTotalSubsystems() { return totalSubsystems; }
        public void setTotalSubsystems(int totalSubsystems) { this.totalSubsystems = totalSubsystems; }

        public int getSuccessCount() { return successCount; }
        public void setSuccessCount(int successCount) { this.successCount = successCount; }

        public int getFailureCount() { return failureCount; }
        public void setFailureCount(int failureCount) { this.failureCount = failureCount; }

        public boolean isAllSuccess() { return allSuccess; }
        public void setAllSuccess(boolean allSuccess) { this.allSuccess = allSuccess; }

        public LocalDateTime getCompletedAt() { return completedAt; }
        public void setCompletedAt(LocalDateTime completedAt) { this.completedAt = completedAt; }

        public List<LogoutNotificationResult> getSuccessNotifications() { return successNotifications; }
        public List<LogoutNotificationResult> getFailureNotifications() { return failureNotifications; }
    }

    public static class LogoutNotificationResult {
        private String sessionId;
        private String subsystemUrl;
        private String protocol;
        private boolean success;
        private int responseStatusCode;
        private String errorMessage;
        private int attempts;

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public String getSubsystemUrl() { return subsystemUrl; }
        public void setSubsystemUrl(String subsystemUrl) { this.subsystemUrl = subsystemUrl; }

        public String getProtocol() { return protocol; }
        public void setProtocol(String protocol) { this.protocol = protocol; }

        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }

        public int getResponseStatusCode() { return responseStatusCode; }
        public void setResponseStatusCode(int responseStatusCode) { this.responseStatusCode = responseStatusCode; }

        public String getErrorMessage() { return errorMessage; }
        public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

        public int getAttempts() { return attempts; }
        public void setAttempts(int attempts) { this.attempts = attempts; }
    }

    public static class LogoutRequest {
        private String sessionId;
        private String username;
        private String protocol;
        private String timestamp;

        public String getSessionId() { return sessionId; }
        public void setSessionId(String sessionId) { this.sessionId = sessionId; }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getProtocol() { return protocol; }
        public void setProtocol(String protocol) { this.protocol = protocol; }

        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
    }
}

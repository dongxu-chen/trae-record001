package com.sso.session;

import com.sso.entity.UserSession;
import com.sso.repository.UserSessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@RequiredArgsConstructor
public class SessionManager {

    private final UserSessionRepository userSessionRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final SingleLogoutHandler singleLogoutHandler;

    private static final String USER_SESSIONS_KEY = "sso:user:sessions:";
    private static final String SESSION_METADATA_KEY = "sso:session:metadata:";

    public List<UserSession> getActiveSessions(String username) {
        return userSessionRepository.findByUsernameAndActiveTrue(username);
    }

    public List<UserSession> getActiveSessions(Long userId) {
        return userSessionRepository.findByUserIdAndActiveTrue(userId);
    }

    public void invalidateSession(String sessionId) {
        userSessionRepository.invalidateSession(sessionId);
        String sessionKey = "sso:session:" + sessionId;
        redisTemplate.delete(sessionKey);
        log.info("Session invalidated: {}", sessionId);
    }

    public void invalidateAllUserSessions(String username) {
        List<UserSession> sessions = userSessionRepository.findByUsernameAndActiveTrue(username);
        for (UserSession session : sessions) {
            invalidateSession(session.getSessionId());
        }
        log.info("All sessions invalidated for user: {}", username);
    }

    public void extendSession(String sessionId) {
        userSessionRepository.updateLastActive(sessionId, LocalDateTime.now());
        String sessionKey = "sso:session:" + sessionId;
        redisTemplate.expire(sessionKey, 30, TimeUnit.MINUTES);
    }

    public void registerUserSession(String username, String sessionId) {
        String userSessionsKey = USER_SESSIONS_KEY + username;
        redisTemplate.opsForSet().add(userSessionsKey, sessionId);
        redisTemplate.expire(userSessionsKey, 30, TimeUnit.MINUTES);

        String metadataKey = SESSION_METADATA_KEY + sessionId;
        redisTemplate.opsForHash().put(metadataKey, "username", username);
        redisTemplate.opsForHash().put(metadataKey, "createdAt", LocalDateTime.now().toString());
        redisTemplate.expire(metadataKey, 30, TimeUnit.MINUTES);

        log.debug("Session registered for user: {}, session: {}", username, sessionId);
    }

    public Set<Object> getUserSessions(String username) {
        String userSessionsKey = USER_SESSIONS_KEY + username;
        Set<Object> members = redisTemplate.opsForSet().members(userSessionsKey);
        return members != null ? members : Collections.emptySet();
    }

    public boolean isSessionValid(String sessionId) {
        UserSession userSession = userSessionRepository.findBySessionId(sessionId).orElse(null);
        if (userSession == null || !userSession.isActive()) {
            return false;
        }

        if (userSession.getExpiresAt() != null && userSession.getExpiresAt().isBefore(LocalDateTime.now())) {
            return false;
        }

        String sessionKey = "sso:session:" + sessionId;
        return Boolean.TRUE.equals(redisTemplate.hasKey(sessionKey));
    }

    public void updateSessionActivity(String sessionId) {
        userSessionRepository.updateLastActive(sessionId, LocalDateTime.now());
    }

    @Scheduled(cron = "0 */5 * * * ?")
    public void cleanupExpiredSessions() {
        log.debug("Starting scheduled session cleanup");
        try {
            singleLogoutHandler.expireSessions();
            log.debug("Scheduled session cleanup completed");
        } catch (Exception e) {
            log.error("Scheduled session cleanup failed", e);
        }
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void cleanupOrphanedSessions() {
        log.debug("Starting orphaned session cleanup");
        try {
            List<UserSession> activeSessions = userSessionRepository.findAll().stream()
                    .filter(UserSession::isActive)
                    .toList();

            for (UserSession session : activeSessions) {
                String sessionKey = "sso:session:" + session.getSessionId();
                if (!Boolean.TRUE.equals(redisTemplate.hasKey(sessionKey))) {
                    userSessionRepository.invalidateSession(session.getSessionId());
                    log.debug("Cleaned orphaned session: {}", session.getSessionId());
                }
            }
            log.debug("Orphaned session cleanup completed");
        } catch (Exception e) {
            log.error("Orphaned session cleanup failed", e);
        }
    }

    public long getActiveSessionCount() {
        return userSessionRepository.findAll().stream()
                .filter(UserSession::isActive)
                .count();
    }

    public long getActiveUserCount() {
        return userSessionRepository.findAll().stream()
                .filter(UserSession::isActive)
                .map(UserSession::getUsername)
                .distinct()
                .count();
    }
}

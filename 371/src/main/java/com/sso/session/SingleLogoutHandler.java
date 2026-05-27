package com.sso.session;

import com.sso.entity.UserSession;
import com.sso.repository.UserSessionRepository;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.logout.LogoutHandler;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

@Slf4j
@Component
@RequiredArgsConstructor
public class SingleLogoutHandler implements LogoutHandler {

    private final UserSessionRepository userSessionRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final SynchronousLogoutHandler synchronousLogoutHandler;

    @Override
    public void logout(HttpServletRequest request, HttpServletResponse response, Authentication authentication) {
        if (authentication == null) {
            return;
        }

        String username = authentication.getName();
        HttpSession session = request.getSession(false);

        if (session != null) {
            String sessionId = session.getId();
            log.info("Single logout initiated for user: {}, session: {}", username, sessionId);

            boolean useSynchronousSlo = Boolean.parseBoolean(
                    request.getParameter("synchronous"));

            if (useSynchronousSlo) {
                performSynchronousLogout(username, sessionId, request, response);
            } else {
                performAsynchronousLogout(username, sessionId);
            }

            log.info("Single logout completed for user: {}", username);
        }
    }

    private void performSynchronousLogout(String username, String sessionId, 
                                          HttpServletRequest request, HttpServletResponse response) {
        log.info("Performing synchronous SLO for user: {}, session: {}", username, sessionId);

        SynchronousLogoutHandler.LogoutResult result = 
                synchronousLogoutHandler.performSynchronousLogout(username, sessionId);

        request.getSession().setAttribute("sloResult", result);

        if (!result.isAllSuccess()) {
            log.warn("Synchronous SLO had {} failures out of {} subsystems", 
                    result.getFailureCount(), result.getTotalSubsystems());
        }
    }

    private void performAsynchronousLogout(String username, String sessionId) {
        log.info("Performing asynchronous SLO for user: {}, session: {}", username, sessionId);

        invalidateCurrentSession(sessionId);
        invalidateAllUserSessions(username);
        cleanupRedisSessions(username);
        notifyServiceProviders(username, sessionId);
    }

    private void invalidateCurrentSession(String sessionId) {
        userSessionRepository.invalidateSession(sessionId);
        log.debug("Invalidated current session: {}", sessionId);
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
                        Object sessionAttrs = redisTemplate.opsForHash().get(key, "sessionAttr:SPRING_SECURITY_CONTEXT");
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

    private void notifyServiceProviders(String username, String sessionId) {
        List<UserSession> sessions = userSessionRepository.findByUsernameAndActiveTrue(username);
        for (UserSession session : sessions) {
            String protocol = session.getProtocol();
            if (protocol == null) {
                continue;
            }

            switch (protocol) {
                case "SAML2":
                    notifySaml2Provider(session);
                    break;
                case "OAUTH2":
                    notifyOAuth2Provider(session);
                    break;
                case "CAS":
                    notifyCasProvider(session);
                    break;
                default:
                    log.debug("No SLO notification needed for protocol: {}", protocol);
            }
        }
    }

    private void notifySaml2Provider(UserSession session) {
        log.debug("Notifying SAML2 provider about logout for session: {}", session.getSessionId());
    }

    private void notifyOAuth2Provider(UserSession session) {
        log.debug("Notifying OAuth2 provider about logout for session: {}", session.getSessionId());
        try {
            String tokenKey = "sso:oauth2:tokens:" + session.getSessionId();
            Object accessToken = redisTemplate.opsForValue().get(tokenKey);
            if (accessToken != null) {
                redisTemplate.delete(tokenKey);
                log.debug("Revoked OAuth2 access token for session: {}", session.getSessionId());
            }
        } catch (Exception e) {
            log.warn("Failed to revoke OAuth2 token for session: {}", session.getSessionId(), e);
        }
    }

    private void notifyCasProvider(UserSession session) {
        log.debug("Notifying CAS provider about logout for session: {}", session.getSessionId());
    }

    public void forceLogoutUser(String username) {
        log.info("Force logout requested for user: {}", username);
        invalidateAllUserSessions(username);
        cleanupRedisSessions(username);
    }

    public void expireSessions() {
        userSessionRepository.invalidateExpiredSessions(LocalDateTime.now());
        log.debug("Expired sessions cleaned up");
    }
}

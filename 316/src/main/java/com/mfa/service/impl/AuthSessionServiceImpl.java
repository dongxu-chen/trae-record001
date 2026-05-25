package com.mfa.service.impl;

import com.mfa.dto.AuthSession;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.service.AuthPolicyService;
import com.mfa.service.AuthSessionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthSessionServiceImpl implements AuthSessionService {

    private static final String SESSION_KEY_PREFIX = "mfa:session:";
    private static final int DEFAULT_SESSION_TIMEOUT_MINUTES = 30;

    private final RedisTemplate<String, Object> redisTemplate;
    private final AuthPolicyService authPolicyService;

    @Override
    public AuthSession createSession(User user, RiskAssessment riskAssessment) {
        String sessionId = UUID.randomUUID().toString();

        AuthSession session = AuthSession.builder()
                .sessionId(sessionId)
                .user(user)
                .status(AuthStatus.IN_PROGRESS)
                .completedFactors(new ArrayList<>())
                .requiredFactors(authPolicyService.determineRequiredFactors(user, riskAssessment))
                .riskAssessment(riskAssessment)
                .createdAt(LocalDateTime.now())
                .lastActivityAt(LocalDateTime.now())
                .maxInactiveMinutes(DEFAULT_SESSION_TIMEOUT_MINUTES)
                .build();

        saveSession(session);
        log.debug("Created auth session for user: {}, sessionId: {}", user.getUsername(), sessionId);

        return session;
    }

    @Override
    public Optional<AuthSession> getSession(String sessionId) {
        String key = buildKey(sessionId);
        AuthSession session = (AuthSession) redisTemplate.opsForValue().get(key);

        if (session != null && session.isExpired()) {
            log.debug("Auth session expired: {}", sessionId);
            invalidateSession(sessionId);
            return Optional.empty();
        }

        return Optional.ofNullable(session);
    }

    @Override
    public void updateSession(AuthSession session) {
        session.setLastActivityAt(LocalDateTime.now());
        saveSession(session);
        log.debug("Updated auth session: {}", session.getSessionId());
    }

    @Override
    public void invalidateSession(String sessionId) {
        String key = buildKey(sessionId);
        redisTemplate.delete(key);
        log.debug("Invalidated auth session: {}", sessionId);
    }

    @Override
    public void refreshSession(String sessionId) {
        getSession(sessionId).ifPresent(session -> {
            session.setLastActivityAt(LocalDateTime.now());
            saveSession(session);
            log.debug("Refreshed auth session: {}", sessionId);
        });
    }

    private void saveSession(AuthSession session) {
        String key = buildKey(session.getSessionId());
        redisTemplate.opsForValue().set(key, session, session.getMaxInactiveMinutes(), TimeUnit.MINUTES);
    }

    private String buildKey(String sessionId) {
        return SESSION_KEY_PREFIX + sessionId;
    }
}

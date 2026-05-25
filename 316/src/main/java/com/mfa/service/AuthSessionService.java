package com.mfa.service;

import com.mfa.dto.AuthSession;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;

import java.util.Optional;

public interface AuthSessionService {

    AuthSession createSession(User user, RiskAssessment riskAssessment);

    Optional<AuthSession> getSession(String sessionId);

    void updateSession(AuthSession session);

    void invalidateSession(String sessionId);

    void refreshSession(String sessionId);
}

package com.mfa.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.AuthLog;
import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthLogRepository;
import com.mfa.service.AuditLogService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.Base64;
import java.util.List;
import java.util.Objects;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuditLogServiceImpl implements AuditLogService {

    private final AuthLogRepository authLogRepository;
    private final ObjectMapper objectMapper;

    @Override
    @Async
    public AuthLog logAuthentication(String sessionId, User user, FactorType factorType,
                                     AuthStatus status, String message,
                                     HttpServletRequest request, RiskAssessment riskAssessment) {
        AuthLog authLog = new AuthLog();
        authLog.setSessionId(sessionId);
        authLog.setUser(user);
        authLog.setUsername(user != null ? user.getUsername() : null);
        authLog.setFactorType(factorType);
        authLog.setStatus(status);
        authLog.setMessage(message);

        if (request != null) {
            authLog.setIpAddress(getClientIp(request));
            authLog.setUserAgent(truncate(request.getHeader("User-Agent"), 200));
            authLog.setDeviceFingerprint(generateDeviceFingerprint(request));
        }

        if (riskAssessment != null) {
            authLog.setRiskScore(riskAssessment.getScore());
            authLog.setRiskLevel(riskAssessment.getLevel());
            authLog.setStepUpRequired(riskAssessment.isStepUpRequired());
            try {
                authLog.setRiskFactors(objectMapper.writeValueAsString(riskAssessment.getRiskFactors()));
                authLog.setAdditionalInfo(objectMapper.writeValueAsString(riskAssessment.getDetails()));
            } catch (Exception e) {
                log.warn("Failed to serialize risk assessment", e);
            }
        }

        AuthLog saved = authLogRepository.save(authLog);
        log.debug("Auth log saved: session={}, user={}, status={}", sessionId,
                user != null ? user.getUsername() : "anonymous", status);

        return saved;
    }

    @Override
    public List<AuthLog> getUserAuthLogs(Long userId) {
        return authLogRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    @Override
    public Page<AuthLog> getUserAuthLogs(Long userId, Pageable pageable) {
        return authLogRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    @Override
    public List<AuthLog> getSessionAuthLogs(String sessionId) {
        return authLogRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
    }

    @Override
    public Page<AuthLog> getAllAuthLogs(Pageable pageable) {
        return authLogRepository.findAllByOrderByCreatedAtDesc(pageable);
    }

    @Override
    public Page<AuthLog> getAuthLogsByStatus(AuthStatus status, Pageable pageable) {
        return authLogRepository.findByStatusOrderByCreatedAtDesc(status, pageable);
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String xRealIp = request.getHeader("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }
        return request.getRemoteAddr();
    }

    private String generateDeviceFingerprint(HttpServletRequest request) {
        String userAgent = request.getHeader("User-Agent");
        String acceptLanguage = request.getHeader("Accept-Language");
        String acceptEncoding = request.getHeader("Accept-Encoding");

        String raw = userAgent + "|" + acceptLanguage + "|" + acceptEncoding;
        return Base64.getEncoder().encodeToString(Objects.requireNonNullElse(raw, "").getBytes());
    }

    private String truncate(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        return value.length() > maxLength ? value.substring(0, maxLength) : value;
    }
}

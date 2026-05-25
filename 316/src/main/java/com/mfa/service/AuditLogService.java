package com.mfa.service;

import com.mfa.dto.RiskAssessment;
import com.mfa.entity.AuthLog;
import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.List;

public interface AuditLogService {

    AuthLog logAuthentication(String sessionId, User user, FactorType factorType,
                              AuthStatus status, String message,
                              HttpServletRequest request, RiskAssessment riskAssessment);

    List<AuthLog> getUserAuthLogs(Long userId);

    Page<AuthLog> getUserAuthLogs(Long userId, Pageable pageable);

    List<AuthLog> getSessionAuthLogs(String sessionId);

    Page<AuthLog> getAllAuthLogs(Pageable pageable);

    Page<AuthLog> getAuthLogsByStatus(AuthStatus status, Pageable pageable);
}

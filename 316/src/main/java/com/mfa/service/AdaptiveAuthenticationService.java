package com.mfa.service;

import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import jakarta.servlet.http.HttpServletRequest;

import java.util.List;

public interface AdaptiveAuthenticationService {

    RiskAssessment assessAdaptiveRisk(User user, HttpServletRequest request);

    List<FactorType> determineAdaptiveRequiredFactors(User user, RiskAssessment riskAssessment);

    boolean shouldBypassMfa(User user, HttpServletRequest request, RiskAssessment riskAssessment);

    boolean shouldStepUpAuthentication(User user, RiskAssessment currentRisk, int completedFactors);

    String getAuthenticationLevel(RiskAssessment riskAssessment);

    boolean isTrustedDevice(User user, HttpServletRequest request);

    void markDeviceAsTrusted(User user, HttpServletRequest request, int days);
}

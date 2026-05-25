package com.mfa.service;

import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;
import jakarta.servlet.http.HttpServletRequest;

public interface RiskAssessmentService {

    RiskAssessment assessRisk(User user, HttpServletRequest request);
}

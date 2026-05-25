package com.mfa.service;

import com.mfa.dto.RiskAssessment;
import com.mfa.entity.AuthPolicy;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;

import java.util.List;

public interface AuthPolicyService {

    AuthPolicy getDefaultPolicy();

    AuthPolicy getUserPolicy(User user);

    List<FactorType> determineRequiredFactors(User user, RiskAssessment riskAssessment);

    int getRequiredFactorCount(AuthPolicy policy, RiskAssessment riskAssessment);

    boolean isPolicySatisfied(User user, List<FactorType> completedFactors, RiskAssessment riskAssessment);
}

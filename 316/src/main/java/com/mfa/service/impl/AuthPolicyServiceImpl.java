package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.AuthPolicy;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.enums.PolicyOperator;
import com.mfa.enums.RiskLevel;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.repository.AuthPolicyRepository;
import com.mfa.service.AuthPolicyService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthPolicyServiceImpl implements AuthPolicyService {

    private final AuthPolicyRepository authPolicyRepository;
    private final AuthFactorRepository authFactorRepository;
    private final MfaProperties mfaProperties;

    @PostConstruct
    @Transactional
    public void initDefaultPolicy() {
        if (authPolicyRepository.count() == 0) {
            AuthPolicy defaultPolicy = new AuthPolicy();
            defaultPolicy.setName("Default MFA Policy");
            defaultPolicy.setDescription("Default multi-factor authentication policy");
            defaultPolicy.setOperator(PolicyOperator.OR);
            defaultPolicy.setMinRequiredFactors(2);
            defaultPolicy.setRequiredFactors(Arrays.asList(FactorType.TOTP, FactorType.WEBAUTHN));
            defaultPolicy.setOptionalFactors(Arrays.asList(FactorType.SMS, FactorType.EMAIL,
                    FactorType.BIOMETRIC_FINGERPRINT, FactorType.BIOMETRIC_FACE));
            defaultPolicy.setRiskLevel(RiskLevel.LOW);
            defaultPolicy.setAdaptiveEnabled(true);
            defaultPolicy.setLowRiskRequiredFactors(1);
            defaultPolicy.setMediumRiskRequiredFactors(2);
            defaultPolicy.setHighRiskRequiredFactors(3);
            defaultPolicy.setCriticalRiskRequiredFactors(4);
            defaultPolicy.setStepUpEnabled(true);
            defaultPolicy.setEnabled(true);

            authPolicyRepository.save(defaultPolicy);
            log.info("Default authentication policy created");
        }
    }

    @Override
    public AuthPolicy getDefaultPolicy() {
        return authPolicyRepository.findByEnabledTrueAndRiskLevel(RiskLevel.LOW)
                .orElse(authPolicyRepository.findAll().stream()
                        .findFirst()
                        .orElseThrow(() -> new IllegalStateException("No authentication policy found")));
    }

    @Override
    public AuthPolicy getUserPolicy(User user) {
        if (user.getAuthPolicy() != null && user.getAuthPolicy().isEnabled()) {
            return user.getAuthPolicy();
        }
        return getDefaultPolicy();
    }

    @Override
    public List<FactorType> determineRequiredFactors(User user, RiskAssessment riskAssessment) {
        AuthPolicy policy = getUserPolicy(user);
        List<FactorType> userAvailableFactors = authFactorRepository.findVerifiedFactorTypesByUserId(user.getId());
        List<FactorType> requiredFactors = new ArrayList<>();

        if (policy.getRequiredFactors() != null) {
            for (FactorType required : policy.getRequiredFactors()) {
                if (userAvailableFactors.contains(required)) {
                    requiredFactors.add(required);
                }
            }
        }

        int requiredCount = getRequiredFactorCount(policy, riskAssessment);

        if (requiredFactors.size() < requiredCount && policy.getOptionalFactors() != null) {
            for (FactorType optional : policy.getOptionalFactors()) {
                if (userAvailableFactors.contains(optional) && !requiredFactors.contains(optional)) {
                    requiredFactors.add(optional);
                    if (requiredFactors.size() >= requiredCount) {
                        break;
                    }
                }
            }
        }

        if (requiredFactors.isEmpty()) {
            if (!userAvailableFactors.isEmpty()) {
                requiredFactors.addAll(userAvailableFactors.subList(0,
                        Math.min(requiredCount, userAvailableFactors.size())));
            } else {
                requiredFactors.add(FactorType.EMAIL);
                requiredFactors.add(FactorType.SMS);
            }
        }

        log.debug("Determined required factors for user: {}, count: {}, factors: {}",
                user.getUsername(), requiredCount, requiredFactors);

        return requiredFactors;
    }

    @Override
    public int getRequiredFactorCount(AuthPolicy policy, RiskAssessment riskAssessment) {
        if (!policy.isAdaptiveEnabled() || riskAssessment == null) {
            return policy.getMinRequiredFactors();
        }

        RiskLevel riskLevel = RiskLevel.valueOf(riskAssessment.getLevel());

        return switch (riskLevel) {
            case LOW -> policy.getLowRiskRequiredFactors();
            case MEDIUM -> policy.getMediumRiskRequiredFactors();
            case HIGH -> policy.getHighRiskRequiredFactors();
            case CRITICAL -> policy.getCriticalRiskRequiredFactors();
        };
    }

    @Override
    public boolean isPolicySatisfied(User user, List<FactorType> completedFactors, RiskAssessment riskAssessment) {
        if (completedFactors == null || completedFactors.isEmpty()) {
            return false;
        }

        AuthPolicy policy = getUserPolicy(user);
        int requiredCount = getRequiredFactorCount(policy, riskAssessment);
        List<FactorType> requiredFactors = determineRequiredFactors(user, riskAssessment);

        int satisfiedCount = 0;
        if (policy.getOperator() == PolicyOperator.AND) {
            for (FactorType required : requiredFactors) {
                if (completedFactors.contains(required)) {
                    satisfiedCount++;
                }
            }
            return satisfiedCount >= requiredCount;
        } else {
            for (FactorType completed : completedFactors) {
                if (requiredFactors.contains(completed) ||
                        (policy.getOptionalFactors() != null && policy.getOptionalFactors().contains(completed))) {
                    satisfiedCount++;
                }
            }
            return satisfiedCount >= requiredCount;
        }
    }
}

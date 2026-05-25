package com.mfa.dto;

import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthResponse {

    private String sessionId;
    private AuthStatus status;
    private String message;
    private String token;
    private List<FactorType> requiredFactors;
    private List<FactorType> completedFactors;
    private List<FactorType> availableFactors;
    private boolean mfaRequired;
    private int currentStep;
    private int totalSteps;
    private Integer riskScore;
    private String riskLevel;
    private String adaptiveAuthLevel;
    private Boolean stepUpRequired;
}

package com.mfa.dto;

import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthSession {

    private String sessionId;
    private User user;
    private AuthStatus status;
    private List<FactorType> completedFactors;
    private List<FactorType> requiredFactors;
    private RiskAssessment riskAssessment;
    private LocalDateTime createdAt;
    private LocalDateTime lastActivityAt;
    private int maxInactiveMinutes;

    public void addCompletedFactor(FactorType factorType) {
        if (completedFactors == null) {
            completedFactors = new ArrayList<>();
        }
        if (!completedFactors.contains(factorType)) {
            completedFactors.add(factorType);
        }
    }

    public boolean isFactorCompleted(FactorType factorType) {
        return completedFactors != null && completedFactors.contains(factorType);
    }

    public List<FactorType> getRemainingFactors() {
        if (requiredFactors == null || requiredFactors.isEmpty()) {
            return new ArrayList<>();
        }
        List<FactorType> remaining = new ArrayList<>(requiredFactors);
        if (completedFactors != null) {
            remaining.removeAll(completedFactors);
        }
        return remaining;
    }

    public boolean isExpired() {
        if (lastActivityAt == null) {
            return true;
        }
        return lastActivityAt.plusMinutes(maxInactiveMinutes).isBefore(LocalDateTime.now());
    }
}

package com.mfa.service;

import com.mfa.entity.User;
import com.mfa.enums.FactorType;

public interface BiometricService {

    String generateChallenge(String sessionId, User user, FactorType factorType);

    boolean verifyBiometric(String sessionId, User user, FactorType factorType, String biometricData);
}

package com.mfa.service;

import com.mfa.dto.RegisterUserRequest;
import com.mfa.dto.TotpSetupResponse;
import com.mfa.dto.WebAuthnCredential;
import com.mfa.dto.WebAuthnOptionsResponse;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;

import java.util.List;
import java.util.Optional;

public interface UserService {

    User registerUser(RegisterUserRequest request);

    Optional<User> findByUsername(String username);

    List<AuthFactor> getUserFactors(Long userId);

    TotpSetupResponse setupTotp(User user, String issuer);

    boolean verifyTotpSetup(User user, String code);

    WebAuthnOptionsResponse setupWebAuthn(String sessionId, User user);

    boolean verifyWebAuthnSetup(String sessionId, WebAuthnCredential credential, User user);

    boolean setupBiometric(User user, FactorType factorType, String biometricTemplate);

    void deleteFactor(Long userId, Long factorId);

    User getCurrentUser();
}

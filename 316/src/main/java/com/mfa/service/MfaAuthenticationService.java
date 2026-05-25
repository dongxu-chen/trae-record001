package com.mfa.service;

import com.mfa.dto.*;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import jakarta.servlet.http.HttpServletRequest;

public interface MfaAuthenticationService {

    AuthResponse login(LoginRequest request, HttpServletRequest httpRequest);

    AuthResponse sendCode(SendCodeRequest request, HttpServletRequest httpRequest);

    AuthResponse verifyCode(VerifyCodeRequest request, HttpServletRequest httpRequest);

    AuthResponse verifyWebAuthn(String sessionId, WebAuthnAssertion assertion, HttpServletRequest httpRequest);

    AuthResponse verifyBiometric(String sessionId, FactorType factorType, String biometricData, HttpServletRequest httpRequest);

    AuthResponse getAuthStatus(String sessionId);

    AuthResponse registerFactor(User user, FactorType factorType, String name);

    void logout(String sessionId);

    WebAuthnOptionsResponse getPasskeyAuthenticationOptions(String sessionId);

    AuthResponse loginWithPasskey(String sessionId, WebAuthnAssertion assertion, HttpServletRequest httpRequest);

    WebAuthnOptionsResponse getPasskeyRegistrationOptions(String sessionId, User user);
}

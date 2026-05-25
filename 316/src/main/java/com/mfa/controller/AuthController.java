package com.mfa.controller;

import com.mfa.dto.*;
import com.mfa.enums.FactorType;
import com.mfa.service.MfaAuthenticationService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final MfaAuthenticationService mfaAuthenticationService;

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.login(request, httpRequest);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/send-code")
    public ResponseEntity<AuthResponse> sendCode(
            @Valid @RequestBody SendCodeRequest request,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.sendCode(request, httpRequest);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/verify-code")
    public ResponseEntity<AuthResponse> verifyCode(
            @Valid @RequestBody VerifyCodeRequest request,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.verifyCode(request, httpRequest);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/verify-webauthn")
    public ResponseEntity<AuthResponse> verifyWebAuthn(
            @RequestParam String sessionId,
            @RequestBody WebAuthnAssertion assertion,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.verifyWebAuthn(sessionId, assertion, httpRequest);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/verify-biometric")
    public ResponseEntity<AuthResponse> verifyBiometric(
            @RequestParam String sessionId,
            @RequestParam FactorType factorType,
            @RequestBody String biometricData,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.verifyBiometric(
                sessionId, factorType, biometricData, httpRequest);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/status/{sessionId}")
    public ResponseEntity<AuthResponse> getAuthStatus(@PathVariable String sessionId) {
        AuthResponse response = mfaAuthenticationService.getAuthStatus(sessionId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout/{sessionId}")
    public ResponseEntity<Void> logout(@PathVariable String sessionId) {
        mfaAuthenticationService.logout(sessionId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/passkey/options")
    public ResponseEntity<WebAuthnOptionsResponse> getPasskeyAuthenticationOptions(
            @RequestParam(required = false) String sessionId) {
        if (sessionId == null || sessionId.isEmpty()) {
            sessionId = java.util.UUID.randomUUID().toString();
        }
        WebAuthnOptionsResponse response = mfaAuthenticationService.getPasskeyAuthenticationOptions(sessionId);
        return ResponseEntity.ok(WebAuthnOptionsResponse.builder()
                .challenge(response.getChallenge())
                .authenticationOptions(response.getAuthenticationOptions())
                .build());
    }

    @PostMapping("/passkey/login")
    public ResponseEntity<AuthResponse> loginWithPasskey(
            @RequestParam String sessionId,
            @RequestBody WebAuthnAssertion assertion,
            HttpServletRequest httpRequest) {
        AuthResponse response = mfaAuthenticationService.loginWithPasskey(sessionId, assertion, httpRequest);
        return ResponseEntity.ok(response);
    }
}

package com.mfa.controller;

import com.mfa.dto.*;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.service.BiometricDeviceService;
import com.mfa.service.MfaAuthenticationService;
import com.mfa.service.TotpService;
import com.mfa.service.UserService;
import com.mfa.service.WebAuthnService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final WebAuthnService webAuthnService;
    private final BiometricDeviceService biometricDeviceService;
    private final TotpService totpService;
    private final MfaAuthenticationService mfaAuthenticationService;

    @PostMapping("/register")
    public ResponseEntity<User> registerUser(@Valid @RequestBody RegisterUserRequest request) {
        User user = userService.registerUser(request);
        user.setPasswordHash(null);
        return ResponseEntity.ok(user);
    }

    @GetMapping("/factors")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<List<AuthFactor>> getUserFactors() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        List<AuthFactor> factors = userService.getUserFactors(user.getId());
        factors.forEach(f -> {
            f.setSecret(null);
            f.setPublicKey(null);
            f.setCredentialId(null);
        });
        return ResponseEntity.ok(factors);
    }

    @PostMapping("/factors/totp/setup")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<TotpSetupResponse> setupTotp() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        TotpSetupResponse response = userService.setupTotp(user, "MFA Auth Service");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/factors/totp/verify")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Boolean> verifyTotpSetup(@RequestParam String code) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        boolean result = userService.verifyTotpSetup(user, code);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/factors/webauthn/setup")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<WebAuthnOptionsResponse> setupWebAuthn() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        String sessionId = UUID.randomUUID().toString();
        WebAuthnOptionsResponse response = userService.setupWebAuthn(sessionId, user);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/factors/webauthn/verify")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Boolean> verifyWebAuthnSetup(
            @RequestParam String sessionId,
            @RequestBody WebAuthnCredential credential) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        boolean result = userService.verifyWebAuthnSetup(sessionId, credential, user);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/factors/passkey/setup")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<WebAuthnOptionsResponse> setupPasskey() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        String sessionId = UUID.randomUUID().toString();
        WebAuthnOptionsResponse response = mfaAuthenticationService.getPasskeyRegistrationOptions(sessionId, user);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/factors/passkey/verify")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Boolean> verifyPasskeySetup(
            @RequestParam String sessionId,
            @RequestBody WebAuthnCredential credential) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        boolean result = userService.verifyWebAuthnSetup(sessionId, credential, user);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/factors/biometric/setup")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Boolean> setupBiometric(
            @RequestParam FactorType factorType,
            @RequestBody String biometricTemplate) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        boolean result = userService.setupBiometric(user, factorType, biometricTemplate);
        return ResponseEntity.ok(result);
    }

    @DeleteMapping("/factors/{factorId}")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Void> deleteFactor(@PathVariable Long factorId) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        userService.deleteFactor(user.getId(), factorId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/devices/biometric")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<List<BiometricDeviceDTO>> getBiometricDevices() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(biometricDeviceService.getUserDevices(user));
    }

    @PostMapping("/devices/biometric")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<BiometricDeviceDTO> registerBiometricDevice(
            @Valid @RequestBody RegisterBiometricDeviceRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(biometricDeviceService.registerDevice(user, request));
    }

    @PutMapping("/devices/biometric/{deviceId}/name")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<BiometricDeviceDTO> updateDeviceName(
            @PathVariable Long deviceId,
            @RequestBody Map<String, String> body) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        String name = body.get("name");
        if (name == null || name.trim().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(biometricDeviceService.updateDeviceName(user, deviceId, name));
    }

    @PostMapping("/devices/biometric/{deviceId}/revoke")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Void> revokeDevice(
            @PathVariable Long deviceId,
            @Valid @RequestBody(required = false) RevokeDeviceRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        String reason = request != null ? request.getReason() : "用户主动解绑";
        biometricDeviceService.revokeDevice(user, deviceId, reason);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/devices/biometric/{deviceId}/sync")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Void> syncDevice(
            @PathVariable Long deviceId,
            @RequestBody(required = false) Map<String, String> body) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        String devicePublicKey = body != null ? body.get("devicePublicKey") : null;
        biometricDeviceService.syncDevice(user, deviceId, devicePublicKey);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/factors/totp/drift")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> getTotpDriftOffset() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        int drift = totpService.getCurrentDriftOffset(user.getId().toString());
        return ResponseEntity.ok(Map.of(
                "driftOffset", drift,
                "driftSeconds", drift * 30
        ));
    }

    @PostMapping("/factors/totp/drift/reset")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Void> resetTotpDriftOffset() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        totpService.resetDriftOffset(user.getId().toString());
        return ResponseEntity.ok().build();
    }
}

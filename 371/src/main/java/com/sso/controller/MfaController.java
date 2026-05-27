package com.sso.controller;

import com.sso.auth.MfaAuthenticationProvider;
import com.sso.entity.User;
import com.sso.repository.UserRepository;
import com.sso.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

@Slf4j
@RestController
@RequestMapping("/api/mfa")
@RequiredArgsConstructor
public class MfaController {

    private final MfaAuthenticationProvider mfaProvider;
    private final UserService userService;
    private final UserRepository userRepository;

    @PostMapping("/setup")
    public ResponseEntity<Map<String, Object>> setupMfa(@AuthenticationPrincipal UserDetails userDetails) {
        log.info("MFA setup requested for user: {}", userDetails.getUsername());

        User user = userService.findByUsername(userDetails.getUsername())
                .orElseThrow(() -> new RuntimeException("User not found"));

        if (user.isMfaEnabled()) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "MFA is already enabled");
            response.put("remainingBackupCodes", mfaProvider.getRemainingBackupCodes(user));
            return ResponseEntity.badRequest().body(response);
        }

        String secret = mfaProvider.generateMfaSecret();
        String qrCodeUri = mfaProvider.generateQrCodeUri(secret, user.getEmail(), "SSO-Server");
        Set<String> backupCodes = mfaProvider.generateBackupCodes();

        user.setMfaSecret(secret);
        user.setMfaBackupCodes(backupCodes);
        user.setUsedMfaBackupCodes(new java.util.HashSet<>());
        userRepository.save(user);

        Map<String, Object> response = new HashMap<>();
        response.put("secret", secret);
        response.put("qrCodeUri", qrCodeUri);
        response.put("backupCodes", backupCodes);
        response.put("message", "Please scan QR code with your authenticator app and store backup codes securely");

        return ResponseEntity.ok(response);
    }

    @PostMapping("/enable")
    public ResponseEntity<Map<String, Object>> enableMfa(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam String verificationCode) {

        log.info("MFA enable requested for user: {}", userDetails.getUsername());

        User user = userService.findByUsername(userDetails.getUsername())
                .orElseThrow(() -> new RuntimeException("User not found"));

        if (user.getMfaSecret() == null) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "MFA setup not completed. Please call /api/mfa/setup first");
            return ResponseEntity.badRequest().body(response);
        }

        if (!mfaProvider.verifyMfaCode(user.getMfaSecret(), verificationCode)) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "Invalid verification code");
            return ResponseEntity.badRequest().body(response);
        }

        user.setMfaEnabled(true);
        userRepository.save(user);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "MFA enabled successfully");
        response.put("remainingBackupCodes", mfaProvider.getRemainingBackupCodes(user));

        return ResponseEntity.ok(response);
    }

    @PostMapping("/disable")
    public ResponseEntity<Map<String, Object>> disableMfa(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam String verificationCode) {

        log.info("MFA disable requested for user: {}", userDetails.getUsername());

        User user = userService.findByUsername(userDetails.getUsername())
                .orElseThrow(() -> new RuntimeException("User not found"));

        if (!user.isMfaEnabled()) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "MFA is not enabled");
            return ResponseEntity.badRequest().body(response);
        }

        boolean validCode = mfaProvider.verifyMfaCode(user.getMfaSecret(), verificationCode);
        if (!validCode && verificationCode.length() == 8) {
            validCode = mfaProvider.verifyBackupCode(user, verificationCode);
        }

        if (!validCode) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "Invalid verification code or backup code");
            return ResponseEntity.badRequest().body(response);
        }

        user.setMfaEnabled(false);
        user.setMfaSecret(null);
        user.setMfaBackupCodes(new java.util.HashSet<>());
        user.setUsedMfaBackupCodes(new java.util.HashSet<>());
        userRepository.save(user);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "MFA disabled successfully");

        return ResponseEntity.ok(response);
    }

    @PostMapping("/backup-codes/regenerate")
    public ResponseEntity<Map<String, Object>> regenerateBackupCodes(
            @AuthenticationPrincipal UserDetails userDetails,
            @RequestParam String verificationCode) {

        log.info("Backup code regeneration requested for user: {}", userDetails.getUsername());

        User user = userService.findByUsername(userDetails.getUsername())
                .orElseThrow(() -> new RuntimeException("User not found"));

        if (!user.isMfaEnabled()) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "MFA is not enabled");
            return ResponseEntity.badRequest().body(response);
        }

        if (!mfaProvider.verifyMfaCode(user.getMfaSecret(), verificationCode)) {
            Map<String, Object> response = new HashMap<>();
            response.put("error", "Invalid verification code");
            return ResponseEntity.badRequest().body(response);
        }

        Set<String> newBackupCodes = mfaProvider.regenerateBackupCodes(user);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("backupCodes", newBackupCodes);
        response.put("message", "Backup codes regenerated. Store these securely as old codes are now invalid");

        return ResponseEntity.ok(response);
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getMfaStatus(@AuthenticationPrincipal UserDetails userDetails) {
        User user = userService.findByUsername(userDetails.getUsername())
                .orElseThrow(() -> new RuntimeException("User not found"));

        Map<String, Object> response = new HashMap<>();
        response.put("mfaEnabled", user.isMfaEnabled());
        response.put("remainingBackupCodes", mfaProvider.getRemainingBackupCodes(user));

        return ResponseEntity.ok(response);
    }
}

package com.mfa.controller;

import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.service.AdaptiveAuthenticationService;
import com.mfa.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/auth/adaptive")
@RequiredArgsConstructor
public class AdaptiveAuthController {

    private final AdaptiveAuthenticationService adaptiveAuthService;
    private final UserService userService;

    @GetMapping("/risk")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> getAdaptiveRiskAssessment(
            HttpServletRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        RiskAssessment assessment = adaptiveAuthService.assessAdaptiveRisk(user, request);

        Map<String, Object> result = new HashMap<>();
        result.put("riskScore", assessment.getScore());
        result.put("riskLevel", assessment.getLevel());
        result.put("authenticationLevel", adaptiveAuthService.getAuthenticationLevel(assessment));
        result.put("riskFactors", assessment.getRiskFactors());
        result.put("stepUpRequired", assessment.isStepUpRequired());
        result.put("details", assessment.getDetails());

        List<FactorType> requiredFactors = adaptiveAuthService.determineAdaptiveRequiredFactors(
                user, assessment);
        result.put("requiredFactors", requiredFactors);

        return ResponseEntity.ok(result);
    }

    @GetMapping("/device/trusted")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> checkTrustedDevice(HttpServletRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        boolean isTrusted = adaptiveAuthService.isTrustedDevice(user, request);

        Map<String, Object> result = new HashMap<>();
        result.put("isTrusted", isTrusted);

        return ResponseEntity.ok(result);
    }

    @PostMapping("/device/trusted")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> markDeviceAsTrusted(
            @RequestBody Map<String, Integer> requestBody,
            HttpServletRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        int days = requestBody.getOrDefault("days", 30);
        if (days < 1 || days > 365) {
            days = 30;
        }

        adaptiveAuthService.markDeviceAsTrusted(user, request, days);

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "设备已标记为可信，有效期 " + days + " 天");
        result.put("trustedForDays", days);

        return ResponseEntity.ok(result);
    }

    @GetMapping("/level")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> getAuthenticationLevel(HttpServletRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        RiskAssessment assessment = adaptiveAuthService.assessAdaptiveRisk(user, request);
        String authLevel = adaptiveAuthService.getAuthenticationLevel(assessment);
        boolean shouldBypass = adaptiveAuthService.shouldBypassMfa(user, request, assessment);

        Map<String, Object> result = new HashMap<>();
        result.put("authenticationLevel", authLevel);
        result.put("riskScore", assessment.getScore());
        result.put("riskLevel", assessment.getLevel());
        result.put("shouldBypassMfa", shouldBypass);

        return ResponseEntity.ok(result);
    }
}

package com.sso.controller;

import com.sso.entity.UserLoginHistory;
import com.sso.repository.UserLoginHistoryRepository;
import com.sso.service.RiskAssessmentService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/risk")
@RequiredArgsConstructor
public class RiskAssessmentController {

    private final RiskAssessmentService riskAssessmentService;
    private final UserLoginHistoryRepository loginHistoryRepository;

    @PostMapping("/assess")
    public ResponseEntity<Map<String, Object>> assessLoginRisk(
            @AuthenticationPrincipal UserDetails userDetails,
            HttpServletRequest request) {

        RiskAssessmentService.RiskAssessmentResult result = 
                riskAssessmentService.assessLoginRisk(userDetails.getUsername(), request);

        Map<String, Object> response = new HashMap<>();
        response.put("username", result.getUsername());
        response.put("riskLevel", result.getRiskLevel());
        response.put("message", result.getMessage());
        response.put("requireAdditionalVerification", result.isRequireAdditionalVerification());
        response.put("warnings", result.getWarnings());
        response.put("ipAddress", result.getIpAddress());
        response.put("deviceInfo", result.getDeviceInfo());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/history")
    public ResponseEntity<List<UserLoginHistory>> getLoginHistory(
            @AuthenticationPrincipal UserDetails userDetails) {

        List<UserLoginHistory> history = loginHistoryRepository
                .findByUsernameOrderByLoginTimeDesc(userDetails.getUsername());

        return ResponseEntity.ok(history);
    }

    @GetMapping("/history/{username}")
    public ResponseEntity<List<UserLoginHistory>> getUserLoginHistory(
            @PathVariable String username) {

        List<UserLoginHistory> history = loginHistoryRepository
                .findByUsernameOrderByLoginTimeDesc(username);

        return ResponseEntity.ok(history);
    }
}

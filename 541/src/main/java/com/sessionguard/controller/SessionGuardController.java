package com.sessionguard.controller;

import com.sessionguard.config.SessionGuardProperties;
import com.sessionguard.dto.AddThreatRequest;
import com.sessionguard.dto.ApiResponse;
import com.sessionguard.dto.CreateSessionRequest;
import com.sessionguard.dto.InvalidateSessionRequest;
import com.sessionguard.dto.VerifySessionRequest;
import com.sessionguard.model.LocationJumpDetection;
import com.sessionguard.model.RiskAssessment;
import com.sessionguard.model.SessionEvent;
import com.sessionguard.model.SessionProfile;
import com.sessionguard.model.ThreatIntel;
import com.sessionguard.model.UserBehaviorBaseline;
import com.sessionguard.service.ActiveInvalidationService;
import com.sessionguard.service.BehaviorLearningService;
import com.sessionguard.service.LocationJumpDetectionService;
import com.sessionguard.service.SessionGuardService;
import com.sessionguard.service.ThreatIntelService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/session-guard")
@RequiredArgsConstructor
public class SessionGuardController {

    private final SessionGuardService sessionGuardService;
    private final ActiveInvalidationService activeInvalidationService;
    private final SessionGuardProperties properties;
    private final ThreatIntelService threatIntelService;
    private final BehaviorLearningService behaviorLearningService;
    private final LocationJumpDetectionService locationJumpService;

    @PostMapping("/sessions")
    public ResponseEntity<ApiResponse<SessionProfile>> createSession(
            @Valid @RequestBody CreateSessionRequest request,
            HttpServletRequest httpRequest) {

        SessionProfile profile = sessionGuardService.createSession(httpRequest, request.getUserId());
        return ResponseEntity.ok(ApiResponse.ok("Session created", profile));
    }

    @PostMapping("/sessions/verify")
    public ResponseEntity<ApiResponse<RiskAssessment>> verifySession(
            @Valid @RequestBody VerifySessionRequest request,
            HttpServletRequest httpRequest) {

        RiskAssessment assessment = sessionGuardService.verifySession(
                request.getSessionId(),
                httpRequest,
                request.getBusinessScenario());

        if (assessment.getRiskLevel() == RiskAssessment.RiskLevel.CRITICAL
                || assessment.getRiskLevel() == RiskAssessment.RiskLevel.HIGH) {
            sessionGuardService.getSession(request.getSessionId()).ifPresent(profile -> {
                ActiveInvalidationService.InvalidationResult result =
                        activeInvalidationService.handleRiskAssessment(profile, assessment, request.getBusinessScenario());
                if (result.invalidated()) {
                    assessment.setRecommendedAction("SESSION_AUTO_INVALIDATED");
                }
            });
        }

        return ResponseEntity.ok(ApiResponse.ok("Session verified", assessment));
    }

    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<ApiResponse<SessionProfile>> getSession(@PathVariable String sessionId) {
        return sessionGuardService.getSession(sessionId)
                .map(profile -> ResponseEntity.ok(ApiResponse.ok(profile)))
                .orElse(ResponseEntity.ok(ApiResponse.error("Session not found")));
    }

    @GetMapping("/users/{userId}/sessions")
    public ResponseEntity<ApiResponse<List<SessionProfile>>> getUserSessions(@PathVariable String userId) {
        List<SessionProfile> sessions = sessionGuardService.getUserSessions(userId);
        return ResponseEntity.ok(ApiResponse.ok(sessions));
    }

    @GetMapping("/sessions/{sessionId}/risk")
    public ResponseEntity<ApiResponse<RiskAssessment>> getRiskAssessment(@PathVariable String sessionId) {
        return sessionGuardService.getRiskAssessment(sessionId)
                .map(assessment -> ResponseEntity.ok(ApiResponse.ok(assessment)))
                .orElse(ResponseEntity.ok(ApiResponse.error("Risk assessment not found")));
    }

    @GetMapping("/sessions/{sessionId}/history")
    public ResponseEntity<ApiResponse<List<SessionEvent>>> getSessionHistory(@PathVariable String sessionId) {
        List<SessionEvent> events = sessionGuardService.getSessionHistory(sessionId);
        return ResponseEntity.ok(ApiResponse.ok(events));
    }

    @PostMapping("/sessions/{sessionId}/invalidate")
    public ResponseEntity<ApiResponse<Void>> invalidateSession(
            @PathVariable String sessionId,
            @Valid @RequestBody InvalidateSessionRequest request) {

        ActiveInvalidationService.InvalidationResult result =
                activeInvalidationService.forceInvalidate(sessionId, request.getReason());

        if (result.invalidated()) {
            return ResponseEntity.ok(ApiResponse.ok(result.message(), null));
        }
        return ResponseEntity.badRequest().body(ApiResponse.error(result.message()));
    }

    @PostMapping("/users/{userId}/invalidate-all")
    public ResponseEntity<ApiResponse<Void>> invalidateAllUserSessions(
            @PathVariable String userId,
            @RequestParam String reason) {

        ActiveInvalidationService.InvalidationResult result =
                activeInvalidationService.forceInvalidateAllUserSessions(userId, reason);

        return ResponseEntity.ok(ApiResponse.ok(result.message(), null));
    }

    @PostMapping("/ml/train")
    public ResponseEntity<ApiResponse<Void>> trainModel() {
        sessionGuardService.trainModel();
        return ResponseEntity.ok(ApiResponse.ok("ML model training initiated", null));
    }

    @GetMapping("/scenarios")
    public ResponseEntity<ApiResponse<List<Map<String, Object>>>> listBusinessScenarios() {
        List<Map<String, Object>> scenarios = properties.getBusinessScenarios().entrySet().stream()
                .map(entry -> {
                    SessionGuardProperties.BusinessScenarioConfig config = entry.getValue();
                    return Map.<String, Object>of(
                            "name", entry.getKey(),
                            "description", config.getDescription(),
                            "thresholds", config.getThresholds(),
                            "autoInvalidateOnCritical", config.isAutoInvalidateOnCritical(),
                            "requireReauthOnHigh", config.isRequireReauthOnHigh(),
                            "friendlyMessage", config.getFriendlyMessage()
                    );
                })
                .collect(Collectors.toList());

        return ResponseEntity.ok(ApiResponse.ok(scenarios));
    }

    @GetMapping("/config/weights")
    public ResponseEntity<ApiResponse<SessionGuardProperties.RiskWeights>> getRiskWeights() {
        return ResponseEntity.ok(ApiResponse.ok(properties.getRiskWeights()));
    }

    @GetMapping("/users/{userId}/baseline")
    public ResponseEntity<ApiResponse<UserBehaviorBaseline>> getUserBehaviorBaseline(@PathVariable String userId) {
        Optional<UserBehaviorBaseline> baseline = behaviorLearningService.getBaseline(userId);
        return baseline
                .map(b -> ResponseEntity.ok(ApiResponse.ok(b)))
                .orElse(ResponseEntity.ok(ApiResponse.error("Behavior baseline not found for user: " + userId)));
    }

    @GetMapping("/users/{userId}/location-jumps")
    public ResponseEntity<ApiResponse<List<LocationJumpDetection>>> getUserLocationJumps(@PathVariable String userId) {
        List<LocationJumpDetection> jumps = locationJumpService.getJumpHistory(userId);
        return ResponseEntity.ok(ApiResponse.ok(jumps));
    }

    @GetMapping("/threats")
    public ResponseEntity<ApiResponse<List<ThreatIntel>>> listThreats(
            @RequestParam(defaultValue = "100") int limit) {
        List<ThreatIntel> threats = threatIntelService.getAllActiveThreats(limit);
        return ResponseEntity.ok(ApiResponse.ok(threats));
    }

    @GetMapping("/threats/{ipAddress}")
    public ResponseEntity<ApiResponse<ThreatIntel>> getThreatDetails(@PathVariable String ipAddress) {
        Optional<ThreatIntel> threat = threatIntelService.getThreatDetails(ipAddress);
        return threat
                .map(t -> ResponseEntity.ok(ApiResponse.ok(t)))
                .orElse(ResponseEntity.ok(ApiResponse.error("No threat intel found for IP: " + ipAddress)));
    }

    @PostMapping("/threats")
    public ResponseEntity<ApiResponse<Void>> addThreat(@Valid @RequestBody AddThreatRequest request) {
        threatIntelService.addThreatIp(
                request.getIpAddress(),
                request.getThreatType(),
                request.getSeverity(),
                request.getSource() != null ? request.getSource() : "API",
                request.getDescription() != null ? request.getDescription() : "Added via API"
        );
        return ResponseEntity.ok(ApiResponse.ok("Threat IP added successfully", null));
    }

    @DeleteMapping("/threats/{ipAddress}")
    public ResponseEntity<ApiResponse<Void>> removeThreat(@PathVariable String ipAddress) {
        threatIntelService.removeThreatIp(ipAddress);
        return ResponseEntity.ok(ApiResponse.ok("Threat IP removed successfully", null));
    }

    @GetMapping("/threats/check/{ipAddress}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> checkIpThreat(@PathVariable String ipAddress) {
        ThreatIntel threat = threatIntelService.checkIpThreat(ipAddress);
        int riskScore = threatIntelService.getThreatRiskScore(ipAddress);
        boolean isMalicious = threatIntelService.isMaliciousIp(ipAddress);

        Map<String, Object> result = Map.of(
                "ipAddress", ipAddress,
                "isMalicious", isMalicious,
                "riskScore", riskScore,
                "hasThreatIntel", threat != null,
                "threat", threat != null ? threat : "NONE"
        );

        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @GetMapping("/health")
    public ResponseEntity<ApiResponse<String>> health() {
        return ResponseEntity.ok(ApiResponse.ok("Session Guard is running"));
    }
}

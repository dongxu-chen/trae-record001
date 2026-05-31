package com.oauth2.monitor.api;

import com.oauth2.monitor.abuse.TokenAbuseDetector;
import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import com.oauth2.monitor.anomaly.BaselineLearningService;
import com.oauth2.monitor.anomaly.MetricsBaseline;
import com.oauth2.monitor.compliance.ScopeAuditRecord;
import com.oauth2.monitor.compliance.ScopeComplianceService;
import com.oauth2.monitor.metrics.OAuth2Metrics;
import com.oauth2.monitor.risk.ClientRiskProfile;
import com.oauth2.monitor.risk.ClientRiskService;
import com.oauth2.monitor.token.TokenInfo;
import com.oauth2.monitor.token.TokenProbeResult;
import com.oauth2.monitor.token.TokenProbeService;
import com.oauth2.monitor.token.TokenValidationService;
import com.oauth2.monitor.tracing.AuthorizationFlowTrace;
import com.oauth2.monitor.tracing.AuthorizationFlowTraceService;
import com.oauth2.monitor.tracing.TraceContext;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/monitor")
public class MonitorController {

    private final OAuth2Metrics metrics;
    private final TokenValidationService tokenValidationService;
    private final TokenProbeService tokenProbeService;
    private final AuthorizationFlowTraceService traceService;
    private final AlertService alertService;
    private final BaselineLearningService baselineService;
    private final ClientRiskService clientRiskService;
    private final TokenAbuseDetector tokenAbuseDetector;
    private final ScopeComplianceService scopeComplianceService;
    private final ObjectProvider<TraceContext> traceContextProvider;

    public MonitorController(OAuth2Metrics metrics,
                             TokenValidationService tokenValidationService,
                             TokenProbeService tokenProbeService,
                             AuthorizationFlowTraceService traceService,
                             AlertService alertService,
                             BaselineLearningService baselineService,
                             ClientRiskService clientRiskService,
                             TokenAbuseDetector tokenAbuseDetector,
                             ScopeComplianceService scopeComplianceService,
                             ObjectProvider<TraceContext> traceContextProvider) {
        this.metrics = metrics;
        this.tokenValidationService = tokenValidationService;
        this.tokenProbeService = tokenProbeService;
        this.traceService = traceService;
        this.alertService = alertService;
        this.baselineService = baselineService;
        this.clientRiskService = clientRiskService;
        this.tokenAbuseDetector = tokenAbuseDetector;
        this.scopeComplianceService = scopeComplianceService;
        this.traceContextProvider = traceContextProvider;
    }

    @GetMapping("/metrics/summary")
    public ResponseEntity<Map<String, Object>> getMetricsSummary() {
        Map<String, Object> summary = new HashMap<>();

        Map<String, Object> successRates = new HashMap<>();
        successRates.put("authorizationCode", String.format("%.2f%%", metrics.getAuthorizationCodeSuccessRate()));
        successRates.put("token", String.format("%.2f%%", metrics.getTokenSuccessRate()));
        successRates.put("refreshToken", String.format("%.2f%%", metrics.getRefreshTokenSuccessRate()));
        summary.put("successRates", successRates);

        Map<String, Object> tokenStats = new HashMap<>();
        tokenStats.put("activeAccessTokens", tokenValidationService.getActiveTokenCount());
        tokenStats.put("expiredTokens", tokenValidationService.getExpiredTokenCount());
        tokenStats.put("revokedTokens", tokenValidationService.getRevokedTokenCount());
        summary.put("tokenStats", tokenStats);

        Map<String, Object> flowStats = new HashMap<>();
        flowStats.put("activeFlows", traceService.getActiveFlowCount());
        summary.put("flowStats", flowStats);

        summary.put("probeStatistics", tokenProbeService.getProbeStatistics());

        Map<String, Object> riskStats = new HashMap<>();
        riskStats.put("highRiskClients", clientRiskService.getHighRiskClients().size());
        riskStats.put("downgradedClients", clientRiskService.getDowngradedClients().size());
        summary.put("riskStats", riskStats);

        Map<String, Object> abuseStats = new HashMap<>();
        abuseStats.put("trackedTokens", tokenAbuseDetector.getTrackedTokenCount());
        abuseStats.put("blockedTokens", tokenAbuseDetector.getBlockedTokenCount());
        summary.put("abuseStats", abuseStats);

        return ResponseEntity.ok(summary);
    }

    @GetMapping("/tokens")
    public ResponseEntity<Map<String, Object>> getTokenStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("active", tokenValidationService.getActiveTokenCount());
        stats.put("expired", tokenValidationService.getExpiredTokenCount());
        stats.put("revoked", tokenValidationService.getRevokedTokenCount());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/tokens/{tokenValue}")
    public ResponseEntity<TokenInfo> getTokenInfo(@PathVariable String tokenValue) {
        TokenInfo tokenInfo = tokenValidationService.getTokenInfo(tokenValue);
        if (tokenInfo == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(tokenInfo);
    }

    @PostMapping("/tokens/{tokenValue}/validate")
    public ResponseEntity<Map<String, Object>> validateToken(@PathVariable String tokenValue) {
        TokenValidationService.TokenValidationResult result = tokenValidationService.validateToken(tokenValue);
        Map<String, Object> response = new HashMap<>();
        response.put("valid", result.isValid());
        if (!result.isValid()) {
            response.put("errorCode", result.getErrorCode());
            response.put("errorDescription", result.getErrorDescription());
        } else {
            response.put("tokenInfo", result.getTokenInfo());
        }
        return ResponseEntity.ok(response);
    }

    @PostMapping("/tokens/{tokenValue}/revoke")
    public ResponseEntity<Map<String, Object>> revokeToken(@PathVariable String tokenValue) {
        boolean revoked = tokenValidationService.revokeToken(tokenValue);
        Map<String, Object> response = new HashMap<>();
        response.put("revoked", revoked);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/tokens/{tokenValue}/probe")
    public ResponseEntity<TokenProbeResult> probeToken(@PathVariable String tokenValue) {
        TokenProbeResult result = tokenProbeService.probeTokenImmediate(tokenValue);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/tokens/probe/results")
    public ResponseEntity<List<TokenProbeResult>> getProbeResults() {
        return ResponseEntity.ok(tokenProbeService.getLastProbeResults());
    }

    @GetMapping("/tokens/probe/history")
    public ResponseEntity<List<TokenProbeResult>> getProbeHistory(
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(tokenProbeService.getProbeHistory(limit));
    }

    @GetMapping("/tokens/probe/statistics")
    public ResponseEntity<Map<String, Object>> getProbeStatistics() {
        return ResponseEntity.ok(tokenProbeService.getProbeStatistics());
    }

    @GetMapping("/flows")
    public ResponseEntity<List<AuthorizationFlowTrace>> getActiveFlows() {
        return ResponseEntity.ok(traceService.getActiveFlows());
    }

    @GetMapping("/flows/{flowId}")
    public ResponseEntity<AuthorizationFlowTrace> getFlow(@PathVariable String flowId) {
        AuthorizationFlowTrace flow = traceService.getFlow(flowId);
        if (flow == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(flow);
    }

    @GetMapping("/flows/trace/{traceId}")
    public ResponseEntity<List<AuthorizationFlowTrace>> getFlowsByTraceId(@PathVariable String traceId) {
        return ResponseEntity.ok(traceService.getFlowsByTraceId(traceId));
    }

    @GetMapping("/flows/failed")
    public ResponseEntity<List<AuthorizationFlowTrace>> getFailedFlows(
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(traceService.getFailedFlows(limit));
    }

    @GetMapping("/trace/current")
    public ResponseEntity<Map<String, Object>> getCurrentTraceContext() {
        Map<String, Object> response = new HashMap<>();
        try {
            TraceContext ctx = traceContextProvider.getIfAvailable();
            if (ctx != null) {
                response.put("traceId", ctx.getTraceId());
                response.put("spanId", ctx.getSpanId());
                response.put("flowId", ctx.getFlowId());
                response.put("clientId", ctx.getClientId());
                response.put("userId", ctx.getUserId());
                response.put("durationMs", ctx.getDurationMs());
                response.put("attributes", ctx.getAttributes());
            } else {
                response.put("status", "no_active_context");
            }
        } catch (Exception e) {
            response.put("status", "unavailable");
            response.put("error", e.getMessage());
        }
        return ResponseEntity.ok(response);
    }

    @GetMapping("/baselines")
    public ResponseEntity<Map<String, MetricsBaseline>> getAllBaselines() {
        return ResponseEntity.ok(baselineService.getAllBaselines());
    }

    @GetMapping("/baselines/{metricName}")
    public ResponseEntity<MetricsBaseline> getBaseline(@PathVariable String metricName) {
        MetricsBaseline baseline = baselineService.getBaseline(metricName);
        return ResponseEntity.ok(baseline);
    }

    @PostMapping("/baselines/{metricName}/recalculate")
    public ResponseEntity<Map<String, Object>> recalculateBaseline(@PathVariable String metricName) {
        baselineService.triggerBaselineRecalculation(metricName);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "recalculated");
        response.put("metricName", metricName);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/baselines/metrics")
    public ResponseEntity<List<String>> getMonitoredMetrics() {
        return ResponseEntity.ok(baselineService.getMonitoredMetrics());
    }

    @GetMapping("/anomalies/scan")
    public ResponseEntity<List<BaselineLearningService.AnomalyResult>> scanAnomalies() {
        Map<String, Double> currentMetrics = new HashMap<>();
        currentMetrics.put("token_failure_rate", 100.0 - metrics.getTokenSuccessRate()));
        currentMetrics.put("authorization_code_failure_rate", 100.0 - metrics.getAuthorizationCodeSuccessRate()));
        currentMetrics.put("refresh_token_failure_rate", 100.0 - metrics.getRefreshTokenSuccessRate()));
        return ResponseEntity.ok(baselineService.scanForAnomalies(currentMetrics));
    }

    @GetMapping("/anomalies/check/{metricName}")
    public ResponseEntity<BaselineLearningService.AnomalyResult> checkAnomaly(
            @PathVariable String metricName, @RequestParam double value) {
        return ResponseEntity.ok(baselineService.analyzeAnomaly(metricName, value));
    }

    @GetMapping("/risk/clients")
    public ResponseEntity<Map<String, ClientRiskProfile>> getAllRiskProfiles() {
        return ResponseEntity.ok(clientRiskService.getAllRiskProfiles());
    }

    @GetMapping("/risk/clients/{clientId}")
    public ResponseEntity<Map<String, Object>> getClientRisk(@PathVariable String clientId) {
        Map<String, Object> response = new HashMap<>();
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        response.put("clientId", clientId);
        response.put("riskScore", profile.getRiskScore());
        response.put("riskLevel", profile.getRiskLevel().name());
        response.put("riskLevelDescription", profile.getRiskLevel().getDescription());
        response.put("successRate", profile.getSuccessRate());
        response.put("isDowngraded", profile.isDowngradeActive());
        response.put("downgradeAction", profile.getCurrentDowngradeAction().name());
        response.put("downgradeReason", profile.getDowngradeReason());
        response.put("totalRequests", profile.getTotalRequests().get());
        response.put("authenticationFailures", profile.getAuthenticationFailures().get());
        response.put("firstSeen", profile.getFirstSeen());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/risk/clients/high-risk")
    public ResponseEntity<List<ClientRiskProfile>> getHighRiskClients() {
        return ResponseEntity.ok(clientRiskService.getHighRiskClients());
    }

    @GetMapping("/risk/clients/downgraded")
    public ResponseEntity<List<ClientRiskProfile>> getDowngradedClients() {
        return ResponseEntity.ok(clientRiskService.getDowngradedClients());
    }

    @PostMapping("/risk/clients/{clientId}/release")
    public ResponseEntity<Map<String, Object>> releaseClientDowngrade(@PathVariable String clientId) {
        clientRiskService.releaseClientDowngrade(clientId);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "released");
        response.put("clientId", clientId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/risk/clients/{clientId}/reset")
    public ResponseEntity<Map<String, Object>> resetClientRisk(@PathVariable String clientId) {
        clientRiskService.resetClientRisk(clientId);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "reset");
        response.put("clientId", clientId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/abuse/tokens")
    public ResponseEntity<List<Map<String, Object>>> getHighUsageTokens(
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(tokenAbuseDetector.getAbuseAlerts(limit));
    }

    @GetMapping("/abuse/tokens/blocked")
    public ResponseEntity<Set<String>> getBlockedTokens() {
        return ResponseEntity.ok(tokenAbuseDetector.getBlockedTokens());
    }

    @PostMapping("/abuse/tokens/{tokenValue}/block")
    public ResponseEntity<Map<String, Object>> blockToken(
            @PathVariable String tokenValue,
            @RequestParam String clientId,
            @RequestParam String userId,
            @RequestParam String reason) {
        tokenAbuseDetector.blockToken(tokenValue, clientId, userId, reason);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "blocked");
        response.put("tokenValue", maskToken(tokenValue));
        return ResponseEntity.ok(response);
    }

    @PostMapping("/abuse/tokens/{tokenValue}/unblock")
    public ResponseEntity<Map<String, Object>> unblockToken(@PathVariable String tokenValue) {
        tokenAbuseDetector.unblockToken(tokenValue);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "unblocked");
        response.put("tokenValue", maskToken(tokenValue));
        return ResponseEntity.ok(response);
    }

    @GetMapping("/abuse/stats")
    public ResponseEntity<Map<String, Object>> getAbuseStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("trackedTokens", tokenAbuseDetector.getTrackedTokenCount());
        stats.put("blockedTokens", tokenAbuseDetector.getBlockedTokenCount());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/compliance/violations")
    public ResponseEntity<List<ScopeComplianceService.ComplianceViolation>> getComplianceViolations(
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(scopeComplianceService.getRecentViolations(limit)));
    }

    @GetMapping("/compliance/audits")
    public ResponseEntity<List<ScopeAuditRecord>> getComplianceAudits(
            @RequestParam(required = false) String clientId,
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(scopeComplianceService.getAuditRecords(clientId, limit));
    }

    @GetMapping("/compliance/scopes")
    public ResponseEntity<Map<String, Set<String>>> getAllowedClientScopes() {
        return ResponseEntity.ok(scopeComplianceService.getAllClientScopes());
    }

    @GetMapping("/compliance/scopes/sensitive")
    public ResponseEntity<List<String>> getSensitiveScopes() {
        return ResponseEntity.ok(scopeComplianceService.getSensitiveScopes());
    }

    @PostMapping("/compliance/scopes/sensitive/{scope}")
    public ResponseEntity<Map<String, Object>> addSensitiveScope(@PathVariable String scope) {
        scopeComplianceService.addSensitiveScope(scope);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "added");
        response.put("scope", scope);
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/compliance/scopes/sensitive/{scope}")
    public ResponseEntity<Map<String, Object>> removeSensitiveScope(@PathVariable String scope) {
        scopeComplianceService.removeSensitiveScope(scope);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "removed");
        response.put("scope", scope);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/compliance/check")
    public ResponseEntity<ScopeComplianceService.ComplianceCheckResult> checkCompliance(
            @RequestParam String clientId,
            @RequestParam(required = false) String userId,
            @RequestParam Set<String> scopes,
            @RequestParam(defaultValue = "authorization_code") String grantType,
            @RequestParam(required = false) String ipAddress) {
        return ResponseEntity.ok(scopeComplianceService.checkScopes(
                clientId, userId, scopes, grantType, ipAddress)));
    }

    @GetMapping("/alerts")
    public ResponseEntity<List<SecurityEvent>> getActiveAlerts() {
        return ResponseEntity.ok(alertService.getActiveAlerts());
    }

    @GetMapping("/alerts/history")
    public ResponseEntity<List<SecurityEvent>> getAlertHistory(
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(alertService.getAlertHistory(limit));
    }

    @PostMapping("/alerts/{alertKey}/acknowledge")
    public ResponseEntity<Map<String, Object>> acknowledgeAlert(@PathVariable String alertKey) {
        alertService.acknowledgeAlert(alertKey);
        Map<String, Object> response = new HashMap<>();
        response.put("acknowledged", true);
        response.put("alertKey", alertKey);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/alerts/test")
    public ResponseEntity<Map<String, Object>> testAlert(
            @RequestParam SecurityEvent.EventType eventType,
            @RequestParam(defaultValue = "Test alert") String description) {
        alertService.recordSecurityEvent(eventType, description,
                Map.of("test", "true", "clientId", "test-client"));
        Map<String, Object> response = new HashMap<>();
        response.put("status", "alert_recorded");
        response.put("eventType", eventType);
        return ResponseEntity.ok(response);
    }

    private String maskToken(String token) {
        if (token == null || token.length() < 8) {
            return "***";
        }
        return token.substring(0, 4) + "..." + token.substring(token.length() - 4));
    }
}

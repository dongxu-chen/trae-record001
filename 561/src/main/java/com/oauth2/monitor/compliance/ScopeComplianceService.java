package com.oauth2.monitor.compliance;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import com.oauth2.monitor.risk.ClientRiskService;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ScopeComplianceService {

    private final AlertService alertService;
    private final ClientRiskService clientRiskService;
    private final MeterRegistry meterRegistry;

    @Value("${oauth2.monitor.compliance.enabled:true}")
    private boolean complianceEnabled;

    @Value("${oauth2.monitor.compliance.sensitive-scopes:admin,write,delete}")
    private List<String> sensitiveScopes;

    @Value("${oauth2.monitor.compliance.max-scopes-per-token:10}")
    private int maxScopesPerToken;

    @Value("${oauth2.monitor.compliance.audit-enabled:true}")
    private boolean auditEnabled;

    private final Map<String, Set<String>> clientAllowedScopes = new ConcurrentHashMap<>();
    private final Map<String, ScopeAuditRecord> auditRecords = new ConcurrentHashMap<>();
    private final List<ComplianceViolation> violations = Collections.synchronizedList(new ArrayList<>());

    private final Map<String, Counter> scopeCounters = new ConcurrentHashMap<>();
    private final Counter.Builder violationCounterBuilder = Counter.builder("oauth2_compliance_violations_total");

    private static final int MAX_VIOLATIONS = 1000;
    private static final int MAX_AUDIT_RECORDS = 10000;

    public ScopeComplianceService(AlertService alertService, ClientRiskService clientRiskService,
                                   MeterRegistry meterRegistry) {
        this.alertService = alertService;
        this.clientRiskService = clientRiskService;
        this.meterRegistry = meterRegistry;

        violationCounterBuilder.description("Total compliance violations")
                .register(meterRegistry);
    }

    public void registerClientScopes(String clientId, Set<String> allowedScopes) {
        clientAllowedScopes.put(clientId, new HashSet<>(allowedScopes));
        log.info("Registered allowed scopes for client {}: {}", clientId, allowedScopes);
    }

    public void addAllowedScope(String clientId, String scope) {
        clientAllowedScopes.computeIfAbsent(clientId, k -> ConcurrentHashMap.newKeySet())
                .add(scope);
    }

    public void removeAllowedScope(String clientId, String scope) {
        Set<String> scopes = clientAllowedScopes.get(clientId);
        if (scopes != null) {
            scopes.remove(scope);
        }
    }

    public ComplianceCheckResult checkScopes(String clientId, String userId, Set<String> requestedScopes,
                                              String grantType, String ipAddress) {
        if (!complianceEnabled) {
            return ComplianceCheckResult.passed();
        }

        List<Violation> foundViolations = new ArrayList<>();

        checkUnauthorizedScopes(clientId, requestedScopes, foundViolations);
        checkSensitiveScopes(clientId, userId, requestedScopes, ipAddress, foundViolations);
        checkScopeCount(requestedScopes, foundViolations);
        checkScopeEscalation(clientId, requestedScopes, foundViolations);
        checkGrantTypeScopeCompatibility(grantType, requestedScopes, foundViolations);

        if (auditEnabled) {
            recordAudit(clientId, userId, requestedScopes, grantType, ipAddress, foundViolations);
        }

        if (!foundViolations.isEmpty()) {
            handleViolations(clientId, userId, requestedScopes, ipAddress, foundViolations);
            return ComplianceCheckResult.failed(foundViolations);
        }

        recordScopeUsage(clientId, requestedScopes);
        return ComplianceCheckResult.passed();
    }

    private void checkUnauthorizedScopes(String clientId, Set<String> requestedScopes,
                                          List<Violation> violations) {
        Set<String> allowed = clientAllowedScopes.get(clientId);
        if (allowed != null && !allowed.isEmpty()) {
            Set<String> unauthorized = requestedScopes.stream()
                    .filter(scope -> !allowed.contains(scope))
                    .collect(Collectors.toSet());

            if (!unauthorized.isEmpty()) {
                violations.add(new Violation(
                        ViolationType.UNAUTHORIZED_SCOPE,
                        Severity.CRITICAL,
                        "Client requested unauthorized scopes: " + unauthorized,
                        Map.of("unauthorizedScopes", unauthorized)
                ));
            }
        }
    }

    private void checkSensitiveScopes(String clientId, String userId, Set<String> requestedScopes,
                                       String ipAddress, List<Violation> violations) {
        Set<String> requestedSensitive = requestedScopes.stream()
                .filter(sensitiveScopes::contains)
                .collect(Collectors.toSet());

        if (!requestedSensitive.isEmpty()) {
            violations.add(new Violation(
                    ViolationType.SENSITIVE_SCOPE_REQUEST,
                    Severity.HIGH,
                    "Client requested sensitive scopes: " + requestedSensitive,
                    Map.of(
                            "sensitiveScopes", requestedSensitive,
                            "clientId", clientId,
                            "userId", userId,
                            "ipAddress", ipAddress
                    )
            ));
        }
    }

    private void checkScopeCount(Set<String> requestedScopes, List<Violation> violations) {
        if (requestedScopes.size() > maxScopesPerToken) {
            violations.add(new Violation(
                    ViolationType.EXCESSIVE_SCOPES,
                    Severity.MEDIUM,
                    "Too many scopes requested: " + requestedScopes.size() +
                            " (max: " + maxScopesPerToken + ")",
                    Map.of(
                            "requestedCount", requestedScopes.size(),
                            "maxAllowed", maxScopesPerToken
                    )
            ));
        }
    }

    private void checkScopeEscalation(String clientId, Set<String> requestedScopes,
                                       List<Violation> violations) {
        ScopeAuditRecord lastRecord = getLastAuditRecord(clientId);
        if (lastRecord != null) {
            Set<String> newScopes = requestedScopes.stream()
                    .filter(scope -> !lastRecord.getHistoricScopes().contains(scope))
                    .collect(Collectors.toSet());

            if (!newScopes.isEmpty() && newScopes.stream().anyMatch(sensitiveScopes::contains)) {
                violations.add(new Violation(
                        ViolationType.SCOPE_ESCALATION,
                        Severity.HIGH,
                        "Scope escalation detected - new sensitive scopes: " + newScopes,
                        Map.of(
                                "newScopes", newScopes,
                                "previousScopes", lastRecord.getHistoricScopes()
                        )
                ));
            }
        }
    }

    private void checkGrantTypeScopeCompatibility(String grantType, Set<String> requestedScopes,
                                                   List<Violation> violations) {
        if ("client_credentials".equals(grantType)) {
            if (requestedScopes.contains("openid") || requestedScopes.contains("profile")) {
                violations.add(new Violation(
                        ViolationType.GRANT_TYPE_SCOPE_MISMATCH,
                        Severity.MEDIUM,
                        "Client credentials grant should not request OIDC scopes",
                        Map.of("grantType", grantType, "scopes", requestedScopes)
                ));
            }
        }
    }

    private void recordAudit(String clientId, String userId, Set<String> requestedScopes,
                              String grantType, String ipAddress, List<Violation> violations) {
        ScopeAuditRecord record = ScopeAuditRecord.builder()
                .auditId(UUID.randomUUID().toString())
                .clientId(clientId)
                .userId(userId)
                .requestedScopes(new HashSet<>(requestedScopes))
                .grantType(grantType)
                .ipAddress(ipAddress)
                .timestamp(Instant.now())
                .hasViolations(!violations.isEmpty())
                .violations(violations.stream()
                        .map(Violation::getType)
                        .map(Enum::name)
                        .collect(Collectors.toSet()))
                .build();

        auditRecords.put(record.getAuditId(), record);

        ScopeAuditRecord lastClientRecord = getLastAuditRecord(clientId);
        if (lastClientRecord != null) {
            record.addHistoricScopes(lastClientRecord.getHistoricScopes());
        }
        record.addHistoricScopes(requestedScopes);

        cleanupOldAuditRecords();
    }

    private ScopeAuditRecord getLastAuditRecord(String clientId) {
        return auditRecords.values().stream()
                .filter(r -> clientId.equals(r.getClientId()))
                .max(Comparator.comparing(ScopeAuditRecord::getTimestamp))
                .orElse(null);
    }

    private void cleanupOldAuditRecords() {
        if (auditRecords.size() > MAX_AUDIT_RECORDS) {
            List<String> toRemove = auditRecords.values().stream()
                    .sorted(Comparator.comparing(ScopeAuditRecord::getTimestamp))
                    .limit(auditRecords.size() - MAX_AUDIT_RECORDS)
                    .map(ScopeAuditRecord::getAuditId)
                    .toList();

            toRemove.forEach(auditRecords::remove);
        }
    }

    private void handleViolations(String clientId, String userId, Set<String> requestedScopes,
                                   String ipAddress, List<Violation> violations) {
        for (Violation violation : violations) {
            ComplianceViolation cv = new ComplianceViolation(
                    UUID.randomUUID().toString(),
                    clientId,
                    userId,
                    violation,
                    requestedScopes,
                    ipAddress,
                    Instant.now()
            );

            addViolation(cv);
            incrementViolationCounter(violation.getType());

            if (violation.getSeverity() == Severity.CRITICAL ||
                    violation.getSeverity() == Severity.HIGH) {
                alertService.recordSecurityEvent(
                        SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
                        "Compliance violation: " + violation.getType() + " - " + violation.getMessage(),
                        Map.of(
                                "clientId", clientId,
                                "userId", userId,
                                "ipAddress", ipAddress,
                                "requestedScopes", requestedScopes,
                                "violationType", violation.getType().name(),
                                "severity", violation.getSeverity().name(),
                                "details", violation.getDetails()
                        )
                );

                clientRiskService.recordUnusualScopeRequest(clientId, requestedScopes.toString());
            }
        }
    }

    private void recordScopeUsage(String clientId, Set<String> scopes) {
        for (String scope : scopes) {
            scopeCounters.computeIfAbsent(scope, s ->
                    Counter.builder("oauth2_scope_usage_total")
                            .tag("scope", s)
                            .tag("client_id", clientId)
                            .register(meterRegistry)
            ).increment();
        }
    }

    private void incrementViolationCounter(ViolationType type) {
        violationCounterBuilder.tag("type", type.name())
                .register(meterRegistry)
                .increment();
    }

    private void addViolation(ComplianceViolation violation) {
        synchronized (violations) {
            if (violations.size() >= MAX_VIOLATIONS) {
                violations.remove(0);
            }
            violations.add(violation);
        }
    }

    public List<ComplianceViolation> getRecentViolations(int limit) {
        List<ComplianceViolation> result = new ArrayList<>();
        synchronized (violations) {
            int start = Math.max(0, violations.size() - limit);
            result.addAll(violations.subList(start, violations.size()));
        }
        return result;
    }

    public List<ScopeAuditRecord> getAuditRecords(String clientId, int limit) {
        return auditRecords.values().stream()
                .filter(r -> clientId == null || clientId.equals(r.getClientId()))
                .sorted(Comparator.comparing(ScopeAuditRecord::getTimestamp).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public Map<String, Set<String>> getAllClientScopes() {
        return clientAllowedScopes.entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, e -> new HashSet<>(e.getValue())));
    }

    public List<String> getSensitiveScopes() {
        return new ArrayList<>(sensitiveScopes);
    }

    public void addSensitiveScope(String scope) {
        if (!sensitiveScopes.contains(scope)) {
            sensitiveScopes = new ArrayList<>(sensitiveScopes);
            sensitiveScopes.add(scope);
        }
    }

    public void removeSensitiveScope(String scope) {
        sensitiveScopes = sensitiveScopes.stream()
                .filter(s -> !s.equals(scope))
                .collect(Collectors.toList());
    }

    public enum ViolationType {
        UNAUTHORIZED_SCOPE,
        SENSITIVE_SCOPE_REQUEST,
        EXCESSIVE_SCOPES,
        SCOPE_ESCALATION,
        GRANT_TYPE_SCOPE_MISMATCH,
        INVALID_SCOPE_FORMAT
    }

    public enum Severity {
        LOW, MEDIUM, HIGH, CRITICAL
    }

    public record Violation(
            ViolationType type,
            Severity severity,
            String message,
            Map<String, Object> details
    ) {}

    public record ComplianceCheckResult(
            boolean passed,
            List<Violation> violations
    ) {
        public static ComplianceCheckResult passed() {
            return new ComplianceCheckResult(true, Collections.emptyList());
        }

        public static ComplianceCheckResult failed(List<Violation> violations) {
            return new ComplianceCheckResult(false, violations);
        }
    }

    public record ComplianceViolation(
            String violationId,
            String clientId,
            String userId,
            Violation violation,
            Set<String> requestedScopes,
            String ipAddress,
            Instant timestamp
    ) {}
}

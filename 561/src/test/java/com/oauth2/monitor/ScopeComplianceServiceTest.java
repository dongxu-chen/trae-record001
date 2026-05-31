package com.oauth2.monitor;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.compliance.ScopeComplianceService;
import com.oauth2.monitor.risk.ClientRiskService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class ScopeComplianceServiceTest {

    @Mock
    private AlertService alertService;

    @Mock
    private ClientRiskService clientRiskService;

    private ScopeComplianceService scopeComplianceService;

    @BeforeEach
    void setUp() {
        scopeComplianceService = new ScopeComplianceService(alertService, clientRiskService);
    }

    @Test
    void testCheckScopes_ValidScopes() {
        String clientId = "test-client";
        Set<String> scopes = Set.of("read", "profile");
        
        ScopeComplianceService.ComplianceCheckResult result = 
            scopeComplianceService.checkScopes(clientId, "user-1", scopes, "authorization_code", "192.168.1.1");
        
        assertTrue(result.isCompliant());
        assertTrue(result.getViolations().isEmpty());
    }

    @Test
    void testCheckScopes_SensitiveScope() {
        String clientId = "test-client";
        Set<String> scopes = Set.of("read", "admin");
        
        ScopeComplianceService.ComplianceCheckResult result = 
            scopeComplianceService.checkScopes(clientId, "user-1", scopes, "authorization_code", "192.168.1.1");
        
        assertFalse(result.isCompliant());
        assertFalse(result.getViolations().isEmpty());
    }

    @Test
    void testCheckScopes_ExcessiveScopes() {
        String clientId = "test-client";
        Set<String> scopes = Set.of(
            "scope1", "scope2", "scope3", "scope4", "scope5",
            "scope6", "scope7", "scope8", "scope9", "scope10", "scope11"
        );
        
        ScopeComplianceService.ComplianceCheckResult result = 
            scopeComplianceService.checkScopes(clientId, "user-1", scopes, "authorization_code", "192.168.1.1");
        
        assertFalse(result.isCompliant());
        assertTrue(result.getViolations().stream()
            .anyMatch(v -> v.getViolationType() == ScopeComplianceService.ViolationType.EXCESSIVE_SCOPES));
    }

    @Test
    void testAddRemoveSensitiveScope() {
        String newScope = "super-admin";
        
        assertFalse(scopeComplianceService.getSensitiveScopes().contains(newScope));
        
        scopeComplianceService.addSensitiveScope(newScope);
        assertTrue(scopeComplianceService.getSensitiveScopes().contains(newScope));
        
        scopeComplianceService.removeSensitiveScope(newScope);
        assertFalse(scopeComplianceService.getSensitiveScopes().contains(newScope));
    }

    @Test
    void testGetAuditRecords() {
        String clientId = "audit-client";
        Set<String> scopes = Set.of("read", "write");
        
        for (int i = 0; i < 5; i++) {
            scopeComplianceService.checkScopes(clientId, "user-" + i, scopes, "authorization_code", "192.168.1.1");
        }
        
        List<?> audits = scopeComplianceService.getAuditRecords(clientId, 10);
        assertFalse(audits.isEmpty());
        assertTrue(audits.size() >= 5);
    }

    @Test
    void testGetRecentViolations() {
        String clientId = "violation-client";
        Set<String> sensitiveScopes = Set.of("admin", "delete");
        
        for (int i = 0; i < 3; i++) {
            scopeComplianceService.checkScopes(clientId, "user-" + i, sensitiveScopes, "authorization_code", "192.168.1.1");
        }
        
        List<?> violations = scopeComplianceService.getRecentViolations(10);
        assertFalse(violations.isEmpty());
    }

    @Test
    void testCheckScopes_WithHistoricScopes() {
        String clientId = "historic-client";
        Set<String> initialScopes = Set.of("read", "profile");
        Set<String> escalatedScopes = Set.of("read", "profile", "admin");
        
        scopeComplianceService.checkScopes(clientId, "user-1", initialScopes, "authorization_code", "192.168.1.1");
        ScopeComplianceService.ComplianceCheckResult result = 
            scopeComplianceService.checkScopes(clientId, "user-1", escalatedScopes, "authorization_code", "192.168.1.1");
        
        assertFalse(result.isCompliant());
    }

    @Test
    void testGrantTypeScopeCompatibility() {
        String clientId = "test-client";
        Set<String> scopes = Set.of("read");
        
        ScopeComplianceService.ComplianceCheckResult result = 
            scopeComplianceService.checkScopes(clientId, "user-1", scopes, "client_credentials", "192.168.1.1");
        
        assertNotNull(result);
    }
}

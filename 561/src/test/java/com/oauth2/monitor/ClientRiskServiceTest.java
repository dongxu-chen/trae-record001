package com.oauth2.monitor;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.risk.ClientRiskProfile;
import com.oauth2.monitor.risk.ClientRiskService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ClientRiskServiceTest {

    @Mock
    private AlertService alertService;

    private ClientRiskService clientRiskService;

    @BeforeEach
    void setUp() {
        clientRiskService = new ClientRiskService(alertService);
    }

    @Test
    void testGetOrCreateProfile_NewClient() {
        String clientId = "test-client";
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        
        assertNotNull(profile);
        assertEquals(clientId, profile.getClientId());
        assertEquals(ClientRiskProfile.RiskLevel.LOW, profile.getRiskLevel());
        assertFalse(profile.isDowngradeActive());
    }

    @Test
    void testGetOrCreateProfile_ExistingClient() {
        String clientId = "test-client";
        ClientRiskProfile profile1 = clientRiskService.getOrCreateProfile(clientId);
        ClientRiskProfile profile2 = clientRiskService.getOrCreateProfile(clientId);
        
        assertSame(profile1, profile2);
    }

    @Test
    void testRecordAuthenticationFailure_IncreasesScore() {
        String clientId = "test-client";
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        double initialScore = profile.getRiskScore();
        
        for (int i = 0; i < 5; i++) {
            clientRiskService.recordAuthenticationFailure(clientId, "192.168.1.1");
        }
        
        assertTrue(profile.getRiskScore() > initialScore);
        assertEquals(5, profile.getAuthenticationFailures().get());
    }

    @Test
    void testRecordSuspiciousActivity_IncreasesScore() {
        String clientId = "test-client";
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        double initialScore = profile.getRiskScore();
        
        clientRiskService.recordSuspiciousActivity(clientId, "test-reason", Map.of("key", "value"));
        
        assertTrue(profile.getRiskScore() > initialScore);
    }

    @Test
    void testHighRiskClientTriggersDowngrade() {
        String clientId = "high-risk-client";
        
        for (int i = 0; i < 50; i++) {
            clientRiskService.recordAuthenticationFailure(clientId, "192.168.1.1");
        }
        
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        assertTrue(profile.getRiskScore() >= 70);
        assertTrue(profile.isDowngradeActive());
    }

    @Test
    void testGetHighRiskClients() {
        String lowRiskClient = "low-risk";
        String highRiskClient = "high-risk";
        
        clientRiskService.getOrCreateProfile(lowRiskClient);
        
        for (int i = 0; i < 30; i++) {
            clientRiskService.recordAuthenticationFailure(highRiskClient, "192.168.1.1");
        }
        
        List<ClientRiskProfile> highRisk = clientRiskService.getHighRiskClients();
        assertFalse(highRisk.isEmpty());
        assertTrue(highRisk.stream().anyMatch(p -> p.getClientId().equals(highRiskClient)));
        assertFalse(highRisk.stream().anyMatch(p -> p.getClientId().equals(lowRiskClient)));
    }

    @Test
    void testReleaseClientDowngrade() {
        String clientId = "downgraded-client";
        
        for (int i = 0; i < 50; i++) {
            clientRiskService.recordAuthenticationFailure(clientId, "192.168.1.1");
        }
        
        assertTrue(clientRiskService.getOrCreateProfile(clientId).isDowngradeActive());
        
        clientRiskService.releaseClientDowngrade(clientId);
        
        assertFalse(clientRiskService.getOrCreateProfile(clientId).isDowngradeActive());
    }

    @Test
    void testResetClientRisk() {
        String clientId = "reset-client";
        
        for (int i = 0; i < 20; i++) {
            clientRiskService.recordAuthenticationFailure(clientId, "192.168.1.1");
        }
        
        clientRiskService.resetClientRisk(clientId);
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        
        assertEquals(0, profile.getRiskScore());
        assertEquals(ClientRiskProfile.RiskLevel.LOW, profile.getRiskLevel());
        assertEquals(0, profile.getAuthenticationFailures().get());
    }

    @Test
    void testRecordAbnormalScopeRequest() {
        String clientId = "test-client";
        
        clientRiskService.recordAbnormalScopeRequest(clientId, "admin write delete");
        
        ClientRiskProfile profile = clientRiskService.getOrCreateProfile(clientId);
        assertTrue(profile.getAbnormalScopeRequests().get() > 0);
    }
}

package com.oauth2.monitor;

import com.oauth2.monitor.abuse.TokenAbuseDetector;
import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.risk.ClientRiskService;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class TokenAbuseDetectorTest {

    @Mock
    private AlertService alertService;

    @Mock
    private ClientRiskService clientRiskService;

    private TokenAbuseDetector tokenAbuseDetector;

    @BeforeEach
    void setUp() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        tokenAbuseDetector = new TokenAbuseDetector(registry, alertService, clientRiskService);
    }

    @Test
    void testRecordTokenUsage_NewToken() {
        String token = "token-123";
        String clientId = "client-1";
        String userId = "user-1";
        String ip = "192.168.1.1";
        
        tokenAbuseDetector.recordTokenUsage(token, clientId, userId, ip);
        
        assertEquals(1, tokenAbuseDetector.getTrackedTokenCount());
    }

    @Test
    void testIsTokenBlocked_NotBlocked() {
        String token = "token-123";
        assertFalse(tokenAbuseDetector.isTokenBlocked(token));
    }

    @Test
    void testBlockToken() {
        String token = "token-block";
        String clientId = "client-1";
        String userId = "user-1";
        String reason = "abuse detected";
        
        tokenAbuseDetector.blockToken(token, clientId, userId, reason);
        
        assertTrue(tokenAbuseDetector.isTokenBlocked(token));
        assertEquals(1, tokenAbuseDetector.getBlockedTokenCount());
        assertTrue(tokenAbuseDetector.getBlockedTokens().contains(token));
    }

    @Test
    void testUnblockToken() {
        String token = "token-unblock";
        
        tokenAbuseDetector.blockToken(token, "client-1", "user-1", "test");
        assertTrue(tokenAbuseDetector.isTokenBlocked(token));
        
        tokenAbuseDetector.unblockToken(token);
        assertFalse(tokenAbuseDetector.isTokenBlocked(token));
    }

    @Test
    void testHighFrequencyUsageDetection() {
        String token = "high-freq-token";
        String clientId = "client-1";
        String userId = "user-1";
        String ip = "192.168.1.1";
        
        for (int i = 0; i < 150; i++) {
            tokenAbuseDetector.recordTokenUsage(token, clientId, userId, ip);
        }
        
        List<Map<String, Object>> alerts = tokenAbuseDetector.getAbuseAlerts(10);
        assertFalse(alerts.isEmpty());
    }

    @Test
    void testMultiIpAccessDetection() {
        String token = "multi-ip-token";
        String clientId = "client-1";
        String userId = "user-1";
        
        for (int i = 0; i < 10; i++) {
            String ip = "192.168.1." + i;
            tokenAbuseDetector.recordTokenUsage(token, clientId, userId, ip);
        }
        
        Set<String> ips = tokenAbuseDetector.getTokenIps(token);
        assertTrue(ips.size() > 1);
    }

    @Test
    void testCleanupOldTokens() {
        String oldToken = "old-token";
        String clientId = "client-1";
        String userId = "user-1";
        String ip = "192.168.1.1";
        
        tokenAbuseDetector.recordTokenUsage(oldToken, clientId, userId, ip);
        assertEquals(1, tokenAbuseDetector.getTrackedTokenCount());
        
        tokenAbuseDetector.cleanupOldTokens();
    }

    @Test
    void testMaskToken() {
        String longToken = "abcdefghijklmnop";
        String result = TokenAbuseDetector.maskToken(longToken);
        assertTrue(result.startsWith("abcd"));
        assertTrue(result.endsWith("mnop"));
        assertTrue(result.contains("..."));
        
        String shortToken = "abc";
        assertEquals("***", TokenAbuseDetector.maskToken(shortToken));
    }
}

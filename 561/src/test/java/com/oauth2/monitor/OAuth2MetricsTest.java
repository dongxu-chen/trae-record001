package com.oauth2.monitor;

import com.oauth2.monitor.metrics.OAuth2Metrics;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("OAuth2 Metrics Tests")
class OAuth2MetricsTest {

    private OAuth2Metrics metrics;
    private MeterRegistry meterRegistry;

    @BeforeEach
    void setUp() {
        meterRegistry = new SimpleMeterRegistry();
        metrics = new OAuth2Metrics(meterRegistry);
    }

    @Test
    @DisplayName("Test authorization code metrics recording")
    void testAuthorizationCodeMetrics() {
        metrics.recordAuthorizationCodeRequest(true, null, "client1");
        metrics.recordAuthorizationCodeRequest(true, null, "client1");
        metrics.recordAuthorizationCodeRequest(false, "invalid_request", "client1");

        assertEquals(100.0 * 2 / 3, metrics.getAuthorizationCodeSuccessRate(), 0.01);

        assertEquals(3, meterRegistry.get("oauth2.authorization_code.requests_total").counter().count());
        assertEquals(2, meterRegistry.get("oauth2.authorization_code.requests_success").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.authorization_code.requests_failed").counter().count());
    }

    @Test
    @DisplayName("Test token metrics recording with different grant types")
    void testTokenMetrics() {
        metrics.recordTokenRequest("authorization_code", true, null, "client1");
        metrics.recordTokenRequest("client_credentials", true, null, "client2");
        metrics.recordTokenRequest("password", false, "invalid_grant", "client1");

        assertEquals(100.0 * 2 / 3, metrics.getTokenSuccessRate(), 0.01);

        assertEquals(1, meterRegistry.get("oauth2.grant_types.total")
                .tag("grant_type", "authorization_code").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.grant_types.total")
                .tag("grant_type", "client_credentials").counter().count());
    }

    @Test
    @DisplayName("Test error code distribution")
    void testErrorCodeDistribution() {
        metrics.recordTokenRequest("password", false, "invalid_grant", "client1");
        metrics.recordTokenRequest("password", false, "invalid_grant", "client1");
        metrics.recordTokenRequest("password", false, "invalid_client", "client1");

        assertEquals(2, meterRegistry.get("oauth2.errors.total")
                .tag("error_code", "invalid_grant").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.errors.total")
                .tag("error_code", "invalid_client").counter().count());
    }

    @Test
    @DisplayName("Test refresh token metrics")
    void testRefreshTokenMetrics() {
        metrics.recordRefreshTokenRequest(true, null, "client1");
        metrics.recordRefreshTokenRequest(false, "invalid_token", "client1");

        assertEquals(50.0, metrics.getRefreshTokenSuccessRate(), 0.01);
    }

    @Test
    @DisplayName("Test token lifecycle metrics")
    void testTokenLifecycleMetrics() {
        metrics.recordTokenRevoked();
        metrics.recordTokenExpired();
        metrics.recordInvalidTokenAttempt();

        assertEquals(1, meterRegistry.get("oauth2.tokens.revoked_total").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.tokens.expired_total").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.tokens.invalid_attempts_total").counter().count());
    }

    @Test
    @DisplayName("Test client request counting")
    void testClientRequestCounting() {
        metrics.recordTokenRequest("client_credentials", true, null, "client-a");
        metrics.recordTokenRequest("client_credentials", true, null, "client-a");
        metrics.recordTokenRequest("client_credentials", true, null, "client-b");

        assertEquals(2, meterRegistry.get("oauth2.clients.requests_total")
                .tag("client_id", "client-a").counter().count());
        assertEquals(1, meterRegistry.get("oauth2.clients.requests_total")
                .tag("client_id", "client-b").counter().count());
    }

    @Test
    @DisplayName("Test success rate with no requests")
    void testSuccessRateWithNoRequests() {
        assertEquals(100.0, metrics.getAuthorizationCodeSuccessRate());
        assertEquals(100.0, metrics.getTokenSuccessRate());
        assertEquals(100.0, metrics.getRefreshTokenSuccessRate());
    }

    @Test
    @DisplayName("Test timer recording")
    void testTimerRecording() {
        OAuth2Metrics.Timer.Sample sample = metrics.startTokenIssueTimer();
        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        metrics.stopTokenIssueTimer(sample);

        assertNotNull(meterRegistry.get("oauth2.token.issue_latency").timer());
        assertTrue(meterRegistry.get("oauth2.token.issue_latency").timer().count() > 0);
    }

    @Test
    @DisplayName("Test token lifetime distribution")
    void testTokenLifetimeDistribution() {
        metrics.recordTokenLifetime(3600);
        metrics.recordTokenLifetime(7200);
        metrics.recordTokenLifetime(1800);

        assertNotNull(meterRegistry.get("oauth2.token.lifetime_seconds").summary());
        assertEquals(3, meterRegistry.get("oauth2.token.lifetime_seconds").summary().count());
    }

    @Test
    @DisplayName("Test gauge values")
    void testGaugeValues() {
        metrics.recordTokenRequest("authorization_code", true, null, "client1");
        metrics.recordAuthorizationCodeRequest(true, null, "client1");

        assertEquals(1, meterRegistry.get("oauth2.tokens.active_access").gauge().value());
        assertEquals(1, meterRegistry.get("oauth2.authorization_codes.total_issued").gauge().value());
        assertEquals(1, meterRegistry.get("oauth2.tokens.total_issued").gauge().value());
    }
}

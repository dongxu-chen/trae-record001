package com.oauth2.monitor;

import com.oauth2.monitor.metrics.OAuth2Metrics;
import com.oauth2.monitor.token.TokenInfo;
import com.oauth2.monitor.token.TokenValidationService;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Token Validation Service Tests")
class TokenValidationServiceTest {

    private TokenValidationService tokenValidationService;
    private OAuth2Metrics metrics;

    @BeforeEach
    void setUp() {
        metrics = new OAuth2Metrics(new SimpleMeterRegistry());
        tokenValidationService = new TokenValidationService(metrics);
    }

    @Test
    @DisplayName("Test valid token validation")
    void testValidTokenValidation() {
        String tokenValue = "valid-token-12345";
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(tokenValue)
                .tokenType("Bearer")
                .clientId("client1")
                .userId("user1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        TokenValidationService.TokenValidationResult result = tokenValidationService.validateToken(tokenValue);

        assertTrue(result.isValid());
        assertNotNull(result.getTokenInfo());
        assertEquals("client1", result.getTokenInfo().getClientId());
        assertEquals("user1", result.getTokenInfo().getUserId());
    }

    @Test
    @DisplayName("Test invalid token validation - token not found")
    void testInvalidTokenNotFound() {
        TokenValidationService.TokenValidationResult result =
                tokenValidationService.validateToken("non-existent-token");

        assertFalse(result.isValid());
        assertEquals("invalid_token", result.getErrorCode());
        assertEquals("Token not found", result.getErrorDescription());
    }

    @Test
    @DisplayName("Test revoked token validation")
    void testRevokedTokenValidation() {
        String tokenValue = "revoked-token-12345";
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(tokenValue)
                .clientId("client1")
                .userId("user1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .revoked(true)
                .build();

        tokenValidationService.registerToken(tokenInfo);

        TokenValidationService.TokenValidationResult result =
                tokenValidationService.validateToken(tokenValue);

        assertFalse(result.isValid());
        assertEquals("invalid_token", result.getErrorCode());
        assertEquals("Token has been revoked", result.getErrorDescription());
    }

    @Test
    @DisplayName("Test expired token validation")
    void testExpiredTokenValidation() {
        String tokenValue = "expired-token-12345";
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(tokenValue)
                .clientId("client1")
                .userId("user1")
                .issuedAt(Instant.now().minus(2, ChronoUnit.HOURS))
                .expiresAt(Instant.now().minus(1, ChronoUnit.HOURS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        TokenValidationService.TokenValidationResult result =
                tokenValidationService.validateToken(tokenValue);

        assertFalse(result.isValid());
        assertEquals("invalid_token", result.getErrorCode());
        assertEquals("Token has expired", result.getErrorDescription());
    }

    @Test
    @DisplayName("Test token revocation")
    void testTokenRevocation() {
        String tokenValue = "token-to-revoke-12345";
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(tokenValue)
                .clientId("client1")
                .userId("user1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        boolean revoked = tokenValidationService.revokeToken(tokenValue);

        assertTrue(revoked);
        assertTrue(tokenInfo.isRevoked());

        TokenValidationService.TokenValidationResult result =
                tokenValidationService.validateToken(tokenValue);
        assertFalse(result.isValid());
    }

    @Test
    @DisplayName("Test token revocation of non-existent token")
    void testRevokeNonExistentToken() {
        boolean revoked = tokenValidationService.revokeToken("non-existent-token");
        assertFalse(revoked);
    }

    @Test
    @DisplayName("Test token stats counting")
    void testTokenStats() {
        TokenInfo validToken = TokenInfo.builder()
                .tokenValue("valid-token")
                .clientId("client1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .build();

        TokenInfo expiredToken = TokenInfo.builder()
                .tokenValue("expired-token")
                .clientId("client1")
                .issuedAt(Instant.now().minus(2, ChronoUnit.HOURS))
                .expiresAt(Instant.now().minus(1, ChronoUnit.HOURS))
                .build();

        TokenInfo revokedToken = TokenInfo.builder()
                .tokenValue("revoked-token")
                .clientId("client1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .revoked(true)
                .build();

        tokenValidationService.registerToken(validToken);
        tokenValidationService.registerToken(expiredToken);
        tokenValidationService.registerToken(revokedToken);

        assertEquals(1, tokenValidationService.getActiveTokenCount());
        assertEquals(1, tokenValidationService.getExpiredTokenCount());
        assertEquals(1, tokenValidationService.getRevokedTokenCount());
    }

    @Test
    @DisplayName("Test token expiring soon detection")
    void testTokenExpiringSoon() {
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue("expiring-soon-token")
                .clientId("client1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(60, ChronoUnit.SECONDS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        assertTrue(tokenInfo.isExpiringSoon(300));
        assertFalse(tokenInfo.isExpiringSoon(30));
    }

    @Test
    @DisplayName("Test token lifetime recording")
    void testTokenLifetimeRecording() {
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue("lifetime-test-token")
                .clientId("client1")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(3600, ChronoUnit.SECONDS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        assertEquals(3600, tokenInfo.getSecondsUntilExpiry(), 1);
    }

    @Test
    @DisplayName("Test scheduled expiration check")
    void testScheduledExpirationCheck() {
        TokenInfo expiredToken = TokenInfo.builder()
                .tokenValue("scheduled-expired-token")
                .clientId("client1")
                .issuedAt(Instant.now().minus(2, ChronoUnit.HOURS))
                .expiresAt(Instant.now().minus(1, ChronoUnit.HOURS))
                .build();

        tokenValidationService.registerToken(expiredToken);

        assertFalse(expiredToken.isExpired());

        tokenValidationService.checkForExpiredTokens();

        assertTrue(expiredToken.isExpired());
    }

    @Test
    @DisplayName("Test token info retrieval")
    void testGetTokenInfo() {
        String tokenValue = "info-test-token";
        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(tokenValue)
                .clientId("client1")
                .userId("user123")
                .grantType("authorization_code")
                .scope("read write")
                .ipAddress("192.168.1.1")
                .userAgent("TestAgent")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plus(1, ChronoUnit.HOURS))
                .build();

        tokenValidationService.registerToken(tokenInfo);

        TokenInfo retrieved = tokenValidationService.getTokenInfo(tokenValue);
        assertNotNull(retrieved);
        assertEquals("client1", retrieved.getClientId());
        assertEquals("user123", retrieved.getUserId());
        assertEquals("authorization_code", retrieved.getGrantType());
        assertEquals("read write", retrieved.getScope());
        assertEquals("192.168.1.1", retrieved.getIpAddress());
        assertEquals("TestAgent", retrieved.getUserAgent());
    }
}

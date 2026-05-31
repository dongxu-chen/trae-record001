package com.oauth2.monitor.token;

import com.oauth2.monitor.metrics.OAuth2Metrics;
import com.oauth2.monitor.tracing.TraceContext;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Iterator;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class TokenValidationService {

    private final OAuth2Metrics metrics;
    private final ObjectProvider<TraceContext> traceContextProvider;
    private final Map<String, TokenInfo> activeTokens = new ConcurrentHashMap<>();

    private static final long EXPIRY_WARNING_THRESHOLD_SECONDS = 300;

    public TokenValidationService(OAuth2Metrics metrics, ObjectProvider<TraceContext> traceContextProvider) {
        this.metrics = metrics;
        this.traceContextProvider = traceContextProvider;
    }

    public void registerToken(TokenInfo tokenInfo) {
        activeTokens.put(tokenInfo.getTokenValue(), tokenInfo);
        if (tokenInfo.getExpiresAt() != null) {
            long lifetime = java.time.Duration.between(
                    tokenInfo.getIssuedAt(), tokenInfo.getExpiresAt()).getSeconds();
            metrics.recordTokenLifetime(lifetime);
        }
        log.debug("Token registered - clientId: {}, userId: {}, expiresAt: {}",
                tokenInfo.getClientId(), tokenInfo.getUserId(), tokenInfo.getExpiresAt());
    }

    public TokenValidationResult validateToken(String tokenValue) {
        String traceId = getCurrentTraceId();
        TokenInfo tokenInfo = activeTokens.get(tokenValue);

        if (tokenInfo == null) {
            log.warn("Token not found - traceId: {}", traceId);
            metrics.recordInvalidTokenAttempt();
            return TokenValidationResult.invalid("invalid_token", "Token not found");
        }

        if (tokenInfo.isRevoked()) {
            log.warn("Token revoked - tokenValue: {}, traceId: {}",
                    maskToken(tokenValue), traceId);
            metrics.recordInvalidTokenAttempt();
            return TokenValidationResult.invalid("invalid_token", "Token has been revoked");
        }

        if (tokenInfo.isExpired()) {
            log.warn("Token expired - tokenValue: {}, traceId: {}",
                    maskToken(tokenValue), traceId);
            handleExpiredToken(tokenValue, tokenInfo);
            return TokenValidationResult.invalid("invalid_token", "Token has expired");
        }

        if (tokenInfo.isExpiringSoon(EXPIRY_WARNING_THRESHOLD_SECONDS)) {
            log.debug("Token expiring soon - tokenValue: {}, secondsLeft: {}",
                    maskToken(tokenValue), tokenInfo.getSecondsUntilExpiry());
        }

        Timer.Sample sample = metrics.startTokenValidationTimer();
        try {
            return TokenValidationResult.valid(tokenInfo);
        } finally {
            metrics.stopTokenValidationTimer(sample);
        }
    }

    public boolean revokeToken(String tokenValue) {
        TokenInfo tokenInfo = activeTokens.get(tokenValue);
        if (tokenInfo != null && !tokenInfo.isRevoked()) {
            tokenInfo.setRevoked(true);
            metrics.recordTokenRevoked();
            log.info("Token revoked - tokenValue: {}, clientId: {}, userId: {}",
                    maskToken(tokenValue), tokenInfo.getClientId(), tokenInfo.getUserId());
            return true;
        }
        return false;
    }

    @Scheduled(fixedDelayString = "${oauth2.monitor.token-expiration-check.fixed-delay:60000}")
    public void checkForExpiredTokens() {
        Instant now = Instant.now();
        int expiredCount = 0;
        int expiringSoonCount = 0;

        Iterator<Map.Entry<String, TokenInfo>> iterator = activeTokens.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, TokenInfo> entry = iterator.next();
            TokenInfo tokenInfo = entry.getValue();

            if (!tokenInfo.isRevoked() && !tokenInfo.isExpired()) {
                if (tokenInfo.isExpired()) {
                    handleExpiredToken(entry.getKey(), tokenInfo);
                    expiredCount++;
                } else if (tokenInfo.isExpiringSoon(EXPIRY_WARNING_THRESHOLD_SECONDS)) {
                    expiringSoonCount++;
                    log.debug("Token expiring soon - tokenValue: {}, clientId: {}, secondsLeft: {}",
                            maskToken(entry.getKey()),
                            tokenInfo.getClientId(),
                            tokenInfo.getSecondsUntilExpiry());
                }
            }
        }

        if (expiredCount > 0 || expiringSoonCount > 0) {
            log.info("Token expiration check complete - expired: {}, expiringSoon: {}",
                    expiredCount, expiringSoonCount);
        }
    }

    private void handleExpiredToken(String tokenValue, TokenInfo tokenInfo) {
        tokenInfo.setExpired(true);
        metrics.recordTokenExpired();
        log.info("Token expired automatically - tokenValue: {}, clientId: {}, userId: {}",
                maskToken(tokenValue), tokenInfo.getClientId(), tokenInfo.getUserId());
    }

    public TokenInfo getTokenInfo(String tokenValue) {
        return activeTokens.get(tokenValue);
    }

    public int getActiveTokenCount() {
        return (int) activeTokens.values().stream()
                .filter(t -> !t.isRevoked() && !t.isExpired())
                .count();
    }

    public int getExpiredTokenCount() {
        return (int) activeTokens.values().stream()
                .filter(TokenInfo::isExpired)
                .count();
    }

    public int getRevokedTokenCount() {
        return (int) activeTokens.values().stream()
                .filter(TokenInfo::isRevoked)
                .count();
    }

    public List<TokenInfo> getActiveTokens() {
        return new ArrayList<>(activeTokens.values());
    }

    private String maskToken(String token) {
        if (token == null || token.length() < 8) {
            return "***";
        }
        return token.substring(0, 4) + "..." + token.substring(token.length() - 4);
    }

    private String getCurrentTraceId() {
        try {
            return Optional.ofNullable(traceContextProvider.getIfAvailable())
                    .map(TraceContext::getTraceId)
                    .orElse("system-" + System.currentTimeMillis());
        } catch (Exception e) {
            return "system-" + System.currentTimeMillis();
        }
    }

    public static class TokenValidationResult {
        private final boolean valid;
        private final String errorCode;
        private final String errorDescription;
        private final TokenInfo tokenInfo;

        private TokenValidationResult(boolean valid, String errorCode,
                                      String errorDescription, TokenInfo tokenInfo) {
            this.valid = valid;
            this.errorCode = errorCode;
            this.errorDescription = errorDescription;
            this.tokenInfo = tokenInfo;
        }

        public static TokenValidationResult valid(TokenInfo tokenInfo) {
            return new TokenValidationResult(true, null, null, tokenInfo);
        }

        public static TokenValidationResult invalid(String errorCode, String errorDescription) {
            return new TokenValidationResult(false, errorCode, errorDescription, null);
        }

        public boolean isValid() { return valid; }
        public String getErrorCode() { return errorCode; }
        public String getErrorDescription() { return errorDescription; }
        public TokenInfo getTokenInfo() { return tokenInfo; }
    }
}

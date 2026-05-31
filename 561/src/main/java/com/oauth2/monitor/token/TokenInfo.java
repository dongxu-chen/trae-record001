package com.oauth2.monitor.token;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TokenInfo {

    private String tokenValue;
    private String tokenType;
    private String clientId;
    private String userId;
    private Instant issuedAt;
    private Instant expiresAt;
    private boolean revoked;
    private boolean expired;
    private String grantType;
    private String scope;
    private String ipAddress;
    private String userAgent;

    public boolean isExpired() {
        if (expired) {
            return true;
        }
        return expiresAt != null && Instant.now().isAfter(expiresAt);
    }

    public long getSecondsUntilExpiry() {
        if (expiresAt == null) {
            return -1;
        }
        return java.time.Duration.between(Instant.now(), expiresAt).getSeconds();
    }

    public boolean isExpiringSoon(long thresholdSeconds) {
        long secondsUntilExpiry = getSecondsUntilExpiry();
        return secondsUntilExpiry >= 0 && secondsUntilExpiry <= thresholdSeconds;
    }
}

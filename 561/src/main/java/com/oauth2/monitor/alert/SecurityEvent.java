package com.oauth2.monitor.alert;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SecurityEvent {

    private String eventId;
    private EventType eventType;
    private Severity severity;
    private String description;
    private String traceId;
    private String clientId;
    private String userId;
    private String ipAddress;
    private String userAgent;
    private Instant timestamp;
    private Map<String, Object> details;

    public enum EventType {
        AUTHORIZATION_FAILURE,
        TOKEN_FAILURE,
        INVALID_TOKEN,
        RATE_LIMIT_EXCEEDED,
        SUSPICIOUS_ACTIVITY,
        CONCURRENT_SESSIONS,
        UNUSUAL_LOCATION,
        BRUTE_FORCE_ATTEMPT,
        CLIENT_AUTHENTICATION_FAILURE,
        INVALID_GRANT_TYPE,
        EXPIRED_TOKEN_USAGE,
        REVOKED_TOKEN_USAGE,
        HIGH_RISK_CLIENT,
        CLIENT_DOWNGRADED,
        CLIENT_AUTO_BLOCKED,
        TOKEN_ABUSE_DETECTED,
        TOKEN_HIGH_FREQUENCY,
        TOKEN_MULTI_IP_ACCESS,
        TOKEN_BLOCKED,
        TOKEN_UNUSUAL_TIME,
        SCOPE_VIOLATION,
        SENSITIVE_SCOPE_REQUEST,
        SCOPE_ESCALATION,
        EXCESSIVE_SCOPES,
        UNAUTHORIZED_SCOPE
    }

    public enum Severity {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }
}

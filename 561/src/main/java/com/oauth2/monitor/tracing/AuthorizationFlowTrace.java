package com.oauth2.monitor.tracing;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthorizationFlowTrace {

    private String traceId;
    private String flowId;
    private String clientId;
    private String userId;
    private String grantType;
    private String status;
    private String errorCode;
    private String errorDescription;
    private Instant startTime;
    private Instant endTime;
    private long durationMs;
    private String ipAddress;
    private String userAgent;

    @Builder.Default
    private Map<String, String> customAttributes = new HashMap<>();

    public enum FlowStatus {
        STARTED,
        AUTHORIZATION_CODE_ISSUED,
        TOKEN_EXCHANGED,
        COMPLETED,
        FAILED,
        ABORTED
    }

    public enum FlowStep {
        AUTHORIZATION_REQUEST("authorization_request"),
        USER_AUTHENTICATION("user_authentication"),
        USER_CONSENT("user_consent"),
        AUTHORIZATION_CODE_ISSUED("authorization_code_issued"),
        TOKEN_REQUEST("token_request"),
        TOKEN_ISSUED("token_issued"),
        REFRESH_TOKEN_REQUEST("refresh_token_request"),
        TOKEN_REVOKED("token_revoked");

        private final String value;

        FlowStep(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }
}

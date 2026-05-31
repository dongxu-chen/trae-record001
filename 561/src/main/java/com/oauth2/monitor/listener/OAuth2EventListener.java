package com.oauth2.monitor.listener;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import com.oauth2.monitor.token.TokenInfo;
import com.oauth2.monitor.token.TokenValidationService;
import com.oauth2.monitor.tracing.AuthorizationFlowTraceService;
import com.oauth2.monitor.tracing.TraceIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.security.authentication.event.AbstractAuthenticationFailureEvent;
import org.springframework.security.authentication.event.AuthenticationSuccessEvent;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2ErrorCodes;
import org.springframework.security.oauth2.server.authorization.authentication.OAuth2AccessTokenAuthenticationToken;
import org.springframework.security.oauth2.server.authorization.authentication.OAuth2AuthorizationCodeAuthenticationToken;
import org.springframework.security.oauth2.server.authorization.event.OAuth2AuthorizationCodeIssuedEvent;
import org.springframework.security.oauth2.server.authorization.event.OAuth2TokenIssuedEvent;
import org.springframework.security.oauth2.server.authorization.event.OAuth2TokenRevokedEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
public class OAuth2EventListener {

    private final TokenValidationService tokenValidationService;
    private final AuthorizationFlowTraceService traceService;
    private final AlertService alertService;

    public OAuth2EventListener(TokenValidationService tokenValidationService,
                               AuthorizationFlowTraceService traceService,
                               AlertService alertService) {
        this.tokenValidationService = tokenValidationService;
        this.traceService = traceService;
        this.alertService = alertService;
    }

    @EventListener
    public void onAuthorizationCodeIssued(OAuth2AuthorizationCodeIssuedEvent event) {
        String traceId = getCurrentTraceId();
        String clientId = event.getRegisteredClient().getClientId();
        String flowId = extractFlowId();
        String userId = event.getAuthentication().getName();

        log.info("Authorization code issued - clientId: {}, userId: {}, traceId: {}",
                clientId, userId, traceId);

        if (flowId != null) {
            traceService.authorizationCodeIssued(flowId, userId);
        }

        recordSecurityEventForSuccess(clientId, userId, "AUTHORIZATION_CODE_ISSUED");
    }

    @EventListener
    public void onTokenIssued(OAuth2TokenIssuedEvent event) {
        String traceId = getCurrentTraceId();
        String clientId = event.getRegisteredClient().getClientId();
        String flowId = extractFlowId();
        String userId = event.getAuthentication().getName();
        String grantType = extractGrantType(event);

        log.info("Token issued - clientId: {}, userId: {}, grantType: {}, traceId: {}",
                clientId, userId, grantType, traceId);

        TokenInfo tokenInfo = TokenInfo.builder()
                .tokenValue(event.getOAuth2Token().getTokenValue())
                .tokenType(event.getOAuth2Token().getTokenType().getValue())
                .clientId(clientId)
                .userId(userId)
                .issuedAt(event.getOAuth2Token().getIssuedAt() != null ?
                        event.getOAuth2Token().getIssuedAt() : Instant.now())
                .expiresAt(event.getOAuth2Token().getExpiresAt())
                .grantType(grantType)
                .scope(event.getOAuth2Token().getScopes() != null ?
                        String.join(" ", event.getOAuth2Token().getScopes()) : null)
                .ipAddress(getClientIpAddress())
                .userAgent(getUserAgent())
                .build();

        tokenValidationService.registerToken(tokenInfo);

        if (flowId != null) {
            traceService.tokenExchanged(flowId, grantType);
            traceService.completeFlow(flowId);
        }

        recordSecurityEventForSuccess(clientId, userId, "TOKEN_ISSUED");
    }

    @EventListener
    public void onTokenRevoked(OAuth2TokenRevokedEvent event) {
        String traceId = getCurrentTraceId();
        String clientId = event.getRegisteredClient().getClientId();
        String tokenValue = event.getToken();

        log.info("Token revoked - clientId: {}, tokenValue: {}, traceId: {}",
                clientId, maskToken(tokenValue), traceId);

        tokenValidationService.revokeToken(tokenValue);

        alertService.recordSecurityEvent(
                SecurityEvent.EventType.REVOKED_TOKEN_USAGE,
                "Token was revoked by client: " + clientId,
                Map.of("clientId", clientId,
                        "tokenValue", maskToken(tokenValue),
                        "traceId", traceId)
        );
    }

    @EventListener
    public void onAuthenticationSuccess(AuthenticationSuccessEvent event) {
        log.debug("Authentication successful - user: {}", event.getAuthentication().getName());
    }

    @EventListener
    public void onAuthenticationFailure(AbstractAuthenticationFailureEvent event) {
        String traceId = getCurrentTraceId();
        String clientId = extractClientId(event);
        String ipAddress = getClientIpAddress();

        Exception exception = event.getException();
        String errorCode = "authentication_failed";
        String errorDescription = exception.getMessage();

        if (exception instanceof OAuth2AuthenticationException oauth2Ex) {
            OAuth2Error error = oauth2Ex.getError();
            errorCode = error.getErrorCode();
            errorDescription = error.getDescription();

            SecurityEvent.EventType eventType = mapErrorCodeToEventType(errorCode);
            alertService.recordSecurityEvent(
                    eventType,
                    errorDescription,
                    Map.of("clientId", clientId != null ? clientId : "unknown",
                            "errorCode", errorCode,
                            "ipAddress", ipAddress,
                            "traceId", traceId)
            );

            String flowId = extractFlowId();
            if (flowId != null) {
                traceService.failFlow(flowId, errorCode, errorDescription);
            }
        }

        log.warn("Authentication failed - errorCode: {}, clientId: {}, IP: {}, traceId: {}",
                errorCode, clientId, ipAddress, traceId);
    }

    private SecurityEvent.EventType mapErrorCodeToEventType(String errorCode) {
        return switch (errorCode) {
            case OAuth2ErrorCodes.INVALID_CLIENT -> SecurityEvent.EventType.CLIENT_AUTHENTICATION_FAILURE;
            case OAuth2ErrorCodes.INVALID_GRANT -> SecurityEvent.EventType.INVALID_GRANT_TYPE;
            case OAuth2ErrorCodes.INVALID_TOKEN -> SecurityEvent.EventType.INVALID_TOKEN;
            case OAuth2ErrorCodes.UNAUTHORIZED_CLIENT -> SecurityEvent.EventType.CLIENT_AUTHENTICATION_FAILURE;
            default -> SecurityEvent.EventType.TOKEN_FAILURE;
        };
    }

    private String extractFlowId() {
        HttpServletRequest request = getCurrentRequest();
        if (request != null) {
            String state = request.getParameter("state");
            if (state != null && !state.isEmpty()) {
                return state;
            }
            String sessionId = request.getSession(false) != null ?
                    request.getSession().getId() : null;
            if (sessionId != null) {
                return sessionId.substring(0, Math.min(16, sessionId.length()));
            }
        }
        return UUID.randomUUID().toString().substring(0, 16);
    }

    private String extractGrantType(OAuth2TokenIssuedEvent event) {
        if (event.getAuthentication() instanceof OAuth2AccessTokenAuthenticationToken authToken) {
            Object principal = authToken.getPrincipal();
            if (principal instanceof OAuth2AuthorizationCodeAuthenticationToken) {
                return "authorization_code";
            }
        }
        return "client_credentials";
    }

    private String extractClientId(AbstractAuthenticationFailureEvent event) {
        try {
            if (event.getAuthentication() != null) {
                Object principal = event.getAuthentication().getPrincipal();
                if (principal instanceof String) {
                    return (String) principal;
                }
            }
        } catch (Exception e) {
            log.debug("Could not extract clientId from failure event");
        }
        return null;
    }

    private String getClientIpAddress() {
        HttpServletRequest request = getCurrentRequest();
        if (request != null) {
            String xForwardedFor = request.getHeader("X-Forwarded-For");
            if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
                return xForwardedFor.split(",")[0].trim();
            }
            return request.getRemoteAddr();
        }
        return null;
    }

    private String getUserAgent() {
        HttpServletRequest request = getCurrentRequest();
        if (request != null) {
            return request.getHeader("User-Agent");
        }
        return null;
    }

    private HttpServletRequest getCurrentRequest() {
        ServletRequestAttributes attributes =
                (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        return attributes != null ? attributes.getRequest() : null;
    }

    private void recordSecurityEventForSuccess(String clientId, String userId, String action) {
        log.debug("OAuth2 success event - action: {}, clientId: {}, userId: {}",
                action, clientId, userId);
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
}

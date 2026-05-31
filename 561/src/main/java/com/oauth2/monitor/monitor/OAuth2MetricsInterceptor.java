package com.oauth2.monitor.monitor;

import com.oauth2.monitor.metrics.OAuth2Metrics;
import io.micrometer.core.instrument.Timer;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class OAuth2MetricsInterceptor implements Filter {

    private static final Logger log = LoggerFactory.getLogger(OAuth2MetricsInterceptor.class);

    private final OAuth2Metrics metrics;

    public OAuth2MetricsInterceptor(OAuth2Metrics metrics) {
        this.metrics = metrics;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws java.io.IOException, jakarta.servlet.ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        String path = httpRequest.getRequestURI();

        Timer.Sample sample = null;

        if (path.contains("/oauth2/authorize")) {
            sample = metrics.startAuthorizationCodeTimer();
        } else if (path.contains("/oauth2/token")) {
            sample = metrics.startTokenIssueTimer();
        } else if (path.contains("/oauth2/introspect")) {
            sample = metrics.startTokenValidationTimer();
        }

        try {
            chain.doFilter(request, response);

            if (sample != null) {
                if (path.contains("/oauth2/authorize")) {
                    metrics.stopAuthorizationCodeTimer(sample);
                } else if (path.contains("/oauth2/token")) {
                    metrics.stopTokenIssueTimer(sample);
                } else if (path.contains("/oauth2/introspect")) {
                    metrics.stopTokenValidationTimer(sample);
                }
            }

            if (path.contains("/oauth2/authorize")) {
                recordAuthorizationCodeMetrics(httpRequest, httpResponse);
            } else if (path.contains("/oauth2/token")) {
                recordTokenMetrics(httpRequest, httpResponse);
            } else if (path.contains("/oauth2/revoke")) {
                metrics.recordTokenRevoked();
            }

        } catch (Exception e) {
            log.error("Error in OAuth2 metrics interceptor", e);
            throw e;
        }
    }

    private void recordAuthorizationCodeMetrics(HttpServletRequest request, HttpServletResponse response) {
        int status = response.getStatus();
        String clientId = request.getParameter("client_id");
        boolean success = status >= 200 && status < 400;
        String errorCode = null;

        if (!success) {
            errorCode = getErrorCodeFromRequest(request);
        }

        metrics.recordAuthorizationCodeRequest(success, errorCode, clientId);
        log.debug("Authorization code request - clientId: {}, success: {}, error: {}",
                clientId, success, errorCode);
    }

    private void recordTokenMetrics(HttpServletRequest request, HttpServletResponse response) {
        int status = response.getStatus();
        String grantType = request.getParameter("grant_type");
        String clientId = extractClientId(request);
        boolean success = status >= 200 && status < 400;
        String errorCode = null;

        if (!success) {
            errorCode = getErrorCodeFromRequest(request);
            if (errorCode == null) {
                errorCode = "status_" + status;
            }
        }

        if ("refresh_token".equals(grantType)) {
            metrics.recordRefreshTokenRequest(success, errorCode, clientId);
        } else {
            metrics.recordTokenRequest(grantType, success, errorCode, clientId);
        }

        log.debug("Token request - grantType: {}, clientId: {}, success: {}, error: {}",
                grantType, clientId, success, errorCode);
    }

    private String extractClientId(HttpServletRequest request) {
        String clientId = request.getParameter("client_id");
        if (clientId == null) {
            String authHeader = request.getHeader("Authorization");
            if (authHeader != null && authHeader.startsWith("Basic ")) {
                clientId = "basic_auth_client";
            }
        }
        return clientId;
    }

    private String getErrorCodeFromRequest(HttpServletRequest request) {
        String error = request.getParameter("error");
        if (error == null) {
            error = (String) request.getAttribute("oauth2_error_code");
        }
        return error;
    }
}

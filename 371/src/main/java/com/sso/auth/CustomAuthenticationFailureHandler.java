package com.sso.auth;

import com.sso.service.CustomUserDetailsService;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationFailureHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Slf4j
@Component
@RequiredArgsConstructor
public class CustomAuthenticationFailureHandler extends SimpleUrlAuthenticationFailureHandler {

    private final CustomUserDetailsService userDetailsService;

    @Override
    public void onAuthenticationFailure(HttpServletRequest request, HttpServletResponse response,
                                        AuthenticationException exception) throws IOException, ServletException {

        String username = request.getParameter("username");
        String ipAddress = getClientIp(request);

        if (username != null && !username.isEmpty()) {
            userDetailsService.handleLoginFailure(username, ipAddress);
        }

        log.warn("Authentication failed for user: {} from IP: {}, reason: {}",
                username, ipAddress, exception.getMessage());

        String errorMessage = "Invalid username or password";
        if (exception.getMessage() != null) {
            if (exception.getMessage().contains("locked")) {
                errorMessage = "Your account has been locked. Please try again later.";
            } else if (exception.getMessage().contains("MFA")) {
                errorMessage = exception.getMessage();
            } else if (exception.getMessage().contains("disabled")) {
                errorMessage = "Your account has been disabled.";
            }
        }

        String redirectUrl = "/login?error=" + java.net.URLEncoder.encode(errorMessage, "UTF-8");

        String redirectUri = request.getParameter("redirect_uri");
        if (redirectUri != null && !redirectUri.isEmpty()) {
            redirectUrl += "&redirect_uri=" + java.net.URLEncoder.encode(redirectUri, "UTF-8");
        }

        getRedirectStrategy().sendRedirect(request, response, redirectUrl);
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }
}

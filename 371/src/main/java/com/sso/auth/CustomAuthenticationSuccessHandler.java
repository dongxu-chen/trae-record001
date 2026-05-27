package com.sso.auth;

import com.sso.entity.UserSession;
import com.sso.repository.UserSessionRepository;
import com.sso.service.CustomUserDetailsService;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;

@Slf4j
@Component
@RequiredArgsConstructor
public class CustomAuthenticationSuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final CustomUserDetailsService userDetailsService;
    private final UserSessionRepository userSessionRepository;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) throws IOException, ServletException {

        String username = authentication.getName();
        String ipAddress = getClientIp(request);
        String userAgent = request.getHeader("User-Agent");
        String clientId = request.getParameter("client_id");
        String protocol = request.getParameter("protocol");

        userDetailsService.handleLoginSuccess(username, ipAddress);

        HttpSession session = request.getSession(false);
        if (session != null) {
            UserSession userSession = new UserSession();
            userSession.setSessionId(session.getId());
            userSession.setUsername(username);
            userSession.setIpAddress(ipAddress);
            userSession.setUserAgent(userAgent);
            userSession.setClientId(clientId);
            userSession.setProtocol(protocol != null ? protocol : "FORM");
            userSession.setLastActive(LocalDateTime.now());
            userSession.setExpiresAt(LocalDateTime.now().plusMinutes(30));
            userSession.setActive(true);

            userSessionRepository.save(userSession);
            log.debug("Created user session: {} for user: {}", session.getId(), username);
        }

        String redirectUrl = determineTargetUrl(request, response, authentication);
        if (response.isCommitted()) {
            log.debug("Response has already been committed. Unable to redirect to " + redirectUrl);
            return;
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

    @Override
    protected String determineTargetUrl(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) {
        String redirectUri = request.getParameter("redirect_uri");
        if (redirectUri != null && !redirectUri.isEmpty()) {
            return redirectUri;
        }
        return "/dashboard";
    }
}

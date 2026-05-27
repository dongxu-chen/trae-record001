package com.sso.auth.saml2;

import com.sso.entity.User;
import com.sso.entity.UserSession;
import com.sso.repository.UserSessionRepository;
import com.sso.service.CustomUserDetailsService;
import com.sso.service.UserService;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.saml2.provider.service.authentication.Saml2AuthenticatedPrincipal;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class Saml2AuthenticationSuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final UserService userService;
    private final CustomUserDetailsService userDetailsService;
    private final UserSessionRepository userSessionRepository;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) throws IOException, ServletException {

        if (authentication.getPrincipal() instanceof Saml2AuthenticatedPrincipal principal) {
            String nameId = principal.getName();
            Map<String, java.util.List<Object>> attributes = principal.getAttributes();

            log.info("SAML2 authentication successful for user: {}", nameId);
            log.debug("SAML2 attributes: {}", attributes);

            String email = getAttribute(attributes, "email", "mail", "Email");
            String firstName = getAttribute(attributes, "firstName", "givenName", "GivenName");
            String lastName = getAttribute(attributes, "lastName", "sn", "Surname");

            User user = userService.findByUsername(nameId).orElse(null);
            if (user == null && email != null) {
                user = userService.findByUsername(email).orElse(null);
            }

            if (user == null) {
                log.warn("User not found for SAML2 principal: {}, creating auto-provisioned user", nameId);
                user = new User();
                user.setUsername(nameId);
                user.setEmail(email != null ? email : nameId + "@saml2.local");
                user.setPassword("{SAML2}");
                user.setFirstName(firstName);
                user.setLastName(lastName);
                user.setDisplayName(firstName != null && lastName != null ? firstName + " " + lastName : nameId);
                user.setEnabled(true);
                user = userService.createUser(user);
            }

            String ipAddress = getClientIp(request);
            userDetailsService.handleLoginSuccess(user.getUsername(), ipAddress);

            HttpSession session = request.getSession(false);
            if (session != null) {
                UserSession userSession = new UserSession();
                userSession.setSessionId(session.getId());
                userSession.setUserId(user.getId());
                userSession.setUsername(user.getUsername());
                userSession.setIpAddress(ipAddress);
                userSession.setUserAgent(request.getHeader("User-Agent"));
                userSession.setProtocol("SAML2");
                userSession.setLastActive(LocalDateTime.now());
                userSession.setExpiresAt(LocalDateTime.now().plusMinutes(30));
                userSession.setActive(true);
                userSessionRepository.save(userSession);
            }
        }

        super.onAuthenticationSuccess(request, response, authentication);
    }

    @SuppressWarnings("unchecked")
    private <T> T getAttribute(Map<String, java.util.List<Object>> attributes, String... keys) {
        for (String key : keys) {
            java.util.List<Object> values = attributes.get(key);
            if (values != null && !values.isEmpty()) {
                return (T) values.get(0);
            }
        }
        return null;
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
        String relayState = request.getParameter("RelayState");
        if (relayState != null && !relayState.isEmpty()) {
            return relayState;
        }
        return "/dashboard";
    }
}

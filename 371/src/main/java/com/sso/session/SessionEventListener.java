package com.sso.session;

import jakarta.servlet.http.HttpSessionEvent;
import jakarta.servlet.http.HttpSessionListener;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SessionEventListener implements HttpSessionListener {

    private final SessionManager sessionManager;
    private final SingleLogoutHandler singleLogoutHandler;

    @Override
    public void sessionCreated(HttpSessionEvent event) {
        String sessionId = event.getSession().getId();
        log.debug("Session created: {}", sessionId);
    }

    @Override
    public void sessionDestroyed(HttpSessionEvent event) {
        String sessionId = event.getSession().getId();
        log.debug("Session destroyed: {}", sessionId);

        sessionManager.invalidateSession(sessionId);

        Authentication authentication = getCurrentAuthentication();
        if (authentication != null) {
            String username = authentication.getName();
            log.info("Session destroyed for user: {}, session: {}", username, sessionId);
        }
    }

    private Authentication getCurrentAuthentication() {
        SecurityContext context = SecurityContextHolder.getContext();
        if (context != null) {
            return context.getAuthentication();
        }
        return null;
    }
}

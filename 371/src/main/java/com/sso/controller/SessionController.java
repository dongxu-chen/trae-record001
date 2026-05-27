package com.sso.controller;

import com.sso.entity.UserSession;
import com.sso.session.SessionManager;
import com.sso.session.SingleLogoutHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final SessionManager sessionManager;
    private final SingleLogoutHandler singleLogoutHandler;

    @GetMapping("/my")
    public ResponseEntity<List<UserSession>> getMySessions(@RequestParam String username) {
        List<UserSession> sessions = sessionManager.getActiveSessions(username);
        return ResponseEntity.ok(sessions);
    }

    @GetMapping("/user/{username}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<List<UserSession>> getUserSessions(@PathVariable String username) {
        List<UserSession> sessions = sessionManager.getActiveSessions(username);
        return ResponseEntity.ok(sessions);
    }

    @PostMapping("/{sessionId}/invalidate")
    public ResponseEntity<Map<String, Object>> invalidateSession(@PathVariable String sessionId) {
        sessionManager.invalidateSession(sessionId);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Session invalidated successfully");
        return ResponseEntity.ok(response);
    }

    @PostMapping("/user/{username}/logout")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> forceLogoutUser(@PathVariable String username) {
        singleLogoutHandler.forceLogoutUser(username);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "All sessions invalidated for user: " + username);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{sessionId}/valid")
    public ResponseEntity<Map<String, Object>> isSessionValid(@PathVariable String sessionId) {
        boolean valid = sessionManager.isSessionValid(sessionId);
        Map<String, Object> response = new HashMap<>();
        response.put("valid", valid);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/stats")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getSessionStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("activeSessions", sessionManager.getActiveSessionCount());
        stats.put("activeUsers", sessionManager.getActiveUserCount());
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/user/{username}/redis")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Set<Object>> getUserRedisSessions(@PathVariable String username) {
        Set<Object> sessions = sessionManager.getUserSessions(username);
        return ResponseEntity.ok(sessions);
    }
}

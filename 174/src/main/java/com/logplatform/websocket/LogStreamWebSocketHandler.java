package com.logplatform.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.logplatform.model.LogEntry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class LogStreamWebSocketHandler extends TextWebSocketHandler {

    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    private final Map<String, String> sessionFilters = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String sessionId = session.getId();
        sessions.put(sessionId, session);
        log.info("WebSocket connection established: {}", sessionId);

        String query = session.getUri() != null ? session.getUri().getQuery() : null;
        if (query != null && query.contains("filter=")) {
            String filter = query.split("filter=")[1].split("&")[0];
            sessionFilters.put(sessionId, java.net.URLDecoder.decode(filter, "UTF-8"));
            log.info("Session {} filter set: {}", sessionId, filter);
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        String sessionId = session.getId();

        try {
            Map<String, Object> msg = objectMapper.readValue(payload, Map.class);
            String action = (String) msg.get("action");

            if ("filter".equals(action)) {
                String filter = (String) msg.get("filter");
                if (filter != null && !filter.trim().isEmpty()) {
                    sessionFilters.put(sessionId, filter);
                    log.debug("Session {} filter updated: {}", sessionId, filter);
                } else {
                    sessionFilters.remove(sessionId);
                    log.debug("Session {} filter cleared", sessionId);
                }
            } else if ("ping".equals(action)) {
                session.sendMessage(new TextMessage("{\"type\":\"pong\"}"));
            }
        } catch (Exception e) {
            log.warn("Failed to parse WebSocket message from {}", sessionId, e);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String sessionId = session.getId();
        sessions.remove(sessionId);
        sessionFilters.remove(sessionId);
        log.info("WebSocket connection closed: {}, status: {}", sessionId, status);
    }

    public void broadcastLog(LogEntry logEntry) {
        if (sessions.isEmpty()) return;

        try {
            String json = objectMapper.writeValueAsString(Map.of(
                    "type", "log",
                    "data", logEntry
            ));
            TextMessage message = new TextMessage(json);

            for (Map.Entry<String, WebSocketSession> entry : sessions.entrySet()) {
                String sessionId = entry.getKey();
                WebSocketSession session = entry.getValue();

                if (session.isOpen()) {
                    String filter = sessionFilters.get(sessionId);
                    if (filter == null || matchesFilter(logEntry, filter)) {
                        try {
                            session.sendMessage(message);
                        } catch (Exception e) {
                            log.warn("Failed to send log to session {}", sessionId, e);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to broadcast log", e);
        }
    }

    private boolean matchesFilter(LogEntry logEntry, String filter) {
        if (filter == null || filter.trim().isEmpty()) return true;

        String lowerFilter = filter.toLowerCase();
        String message = logEntry.getMessage() != null ? logEntry.getMessage().toLowerCase() : "";
        String level = logEntry.getLevel() != null ? logEntry.getLevel().toLowerCase() : "";
        String appName = logEntry.getAppName() != null ? logEntry.getAppName().toLowerCase() : "";
        String logger = logEntry.getLogger() != null ? logEntry.getLogger().toLowerCase() : "";
        String traceId = logEntry.getTraceId() != null ? logEntry.getTraceId().toLowerCase() : "";

        return message.contains(lowerFilter)
                || level.contains(lowerFilter)
                || appName.contains(lowerFilter)
                || logger.contains(lowerFilter)
                || traceId.contains(lowerFilter);
    }

    public int getActiveConnections() {
        return sessions.size();
    }

    public Set<String> getActiveSessions() {
        return Collections.unmodifiableSet(sessions.keySet());
    }
}

package com.filetransfer.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.filetransfer.dto.ProgressMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class ProgressWebSocketHandler extends TextWebSocketHandler {
    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    private final Map<String, String> sessionUploadMap = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String sessionId = session.getId();
        sessions.put(sessionId, session);
        log.info("WebSocket连接建立: {}", sessionId);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        if (payload.startsWith("subscribe:")) {
            String uploadId = payload.substring("subscribe:".length());
            sessionUploadMap.put(session.getId(), uploadId);
            log.info("会话 {} 订阅上传任务: {}", session.getId(), uploadId);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String sessionId = session.getId();
        sessions.remove(sessionId);
        sessionUploadMap.remove(sessionId);
        log.info("WebSocket连接关闭: {}", sessionId);
    }

    public void sendProgress(String uploadId, ProgressMessage message) {
        String jsonMessage;
        try {
            jsonMessage = objectMapper.writeValueAsString(message);
        } catch (Exception e) {
            log.error("序列化进度消息失败", e);
            return;
        }

        for (Map.Entry<String, String> entry : sessionUploadMap.entrySet()) {
            if (entry.getValue().equals(uploadId)) {
                WebSocketSession session = sessions.get(entry.getKey());
                if (session != null && session.isOpen()) {
                    try {
                        session.sendMessage(new TextMessage(jsonMessage));
                    } catch (Exception e) {
                        log.error("发送进度消息失败", e);
                    }
                }
            }
        }
    }

    public void broadcastProgress(ProgressMessage message) {
        String jsonMessage;
        try {
            jsonMessage = objectMapper.writeValueAsString(message);
        } catch (Exception e) {
            log.error("序列化进度消息失败", e);
            return;
        }

        for (WebSocketSession session : sessions.values()) {
            if (session.isOpen()) {
                try {
                    session.sendMessage(new TextMessage(jsonMessage));
                } catch (Exception e) {
                    log.error("广播进度消息失败", e);
                }
            }
        }
    }
}

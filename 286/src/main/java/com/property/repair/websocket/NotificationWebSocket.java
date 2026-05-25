package com.property.repair.websocket;

import com.alibaba.fastjson.JSON;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.websocket.*;
import javax.websocket.server.PathParam;
import javax.websocket.server.ServerEndpoint;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@ServerEndpoint("/ws/notify/{userId}")
public class NotificationWebSocket {

    private static final Map<String, Session> sessionMap = new ConcurrentHashMap<>();

    @OnOpen
    public void onOpen(Session session, @PathParam("userId") String userId) {
        sessionMap.put(userId, session);
        log.info("用户 {} 连接WebSocket，当前在线人数：{}", userId, sessionMap.size());
    }

    @OnClose
    public void onClose(@PathParam("userId") String userId) {
        sessionMap.remove(userId);
        log.info("用户 {} 断开WebSocket，当前在线人数：{}", userId, sessionMap.size());
    }

    @OnMessage
    public void onMessage(String message, Session session) {
        log.info("收到客户端消息：{}", message);
    }

    @OnError
    public void onError(Session session, Throwable error) {
        log.error("WebSocket发生错误", error);
    }

    public void sendMessage(String userId, String type, Object data) {
        Session session = sessionMap.get(userId);
        if (session != null && session.isOpen()) {
            try {
                String message = JSON.toJSONString(Map.of(
                    "type", type,
                    "data", data,
                    "timestamp", System.currentTimeMillis()
                ));
                session.getBasicRemote().sendText(message);
                log.info("向用户 {} 发送消息：{}", userId, message);
            } catch (IOException e) {
                log.error("发送WebSocket消息失败", e);
            }
        }
    }

    public void sendToWorker(Long workerId, String type, Object data) {
        sendMessage(String.valueOf(workerId), type, data);
    }

    public void sendToOwner(Long ownerId, String type, Object data) {
        sendMessage(String.valueOf(ownerId), type, data);
    }

    public void broadcast(String type, Object data) {
        String message = JSON.toJSONString(Map.of(
            "type", type,
            "data", data,
            "timestamp", System.currentTimeMillis()
        ));
        sessionMap.values().forEach(session -> {
            if (session.isOpen()) {
                try {
                    session.getBasicRemote().sendText(message);
                } catch (IOException e) {
                    log.error("广播消息失败", e);
                }
            }
        });
    }
}

package com.alert.service;

import com.alibaba.fastjson.JSON;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.websocket.OnClose;
import javax.websocket.OnError;
import javax.websocket.OnOpen;
import javax.websocket.Session;
import javax.websocket.server.ServerEndpoint;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
@ServerEndpoint("/ws/alerts")
public class WebSocketService {

    private static final Map<String, Session> sessions = new ConcurrentHashMap<>();
    private static final AtomicInteger onlineCount = new AtomicInteger(0);

    @OnOpen
    public void onOpen(Session session) {
        sessions.put(session.getId(), session);
        onlineCount.incrementAndGet();
        log.info("WebSocket连接建立，Session ID: {}, 当前在线数: {}", session.getId(), onlineCount.get());
    }

    @OnClose
    public void onClose(Session session) {
        sessions.remove(session.getId());
        onlineCount.decrementAndGet();
        log.info("WebSocket连接关闭，Session ID: {}, 当前在线数: {}", session.getId(), onlineCount.get());
    }

    @OnError
    public void onError(Session session, Throwable error) {
        log.error("WebSocket发生错误，Session ID: {}", session.getId(), error);
    }

    public void broadcastAlert(Object alert) {
        String message = JSON.toJSONString(Map.of(
                "type", "ALERT",
                "data", alert
        ));
        sendMessage(message);
    }

    public void broadcastAggregation(Object aggregation) {
        String message = JSON.toJSONString(Map.of(
                "type", "AGGREGATION",
                "data", aggregation
        ));
        sendMessage(message);
    }

    private void sendMessage(String message) {
        for (Map.Entry<String, Session> entry : sessions.entrySet()) {
            Session session = entry.getValue();
            if (session.isOpen()) {
                try {
                    session.getBasicRemote().sendText(message);
                } catch (IOException e) {
                    log.error("发送WebSocket消息失败，Session ID: {}", entry.getKey(), e);
                }
            }
        }
    }
}

package com.configcenter.server.service;

import com.configcenter.protocol.SubscribeResponse;
import com.configcenter.server.model.ClientSession;
import io.grpc.stub.StreamObserver;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class ClientSessionManager {

    private final Map<String, ClientSession> sessions = new ConcurrentHashMap<>();

    public void registerSession(ClientSession session) {
        sessions.put(session.getClientId(), session);
        log.info("客户端会话已注册, clientId: {}, serviceName: {}", 
                session.getClientId(), session.getServiceName());
    }

    public void unregisterSession(String clientId) {
        ClientSession session = sessions.remove(clientId);
        if (session != null) {
            log.info("客户端会话已注销, clientId: {}, serviceName: {}", 
                    clientId, session.getServiceName());
        }
    }

    public ClientSession getSession(String clientId) {
        return sessions.get(clientId);
    }

    public void updateHeartbeat(String clientId) {
        ClientSession session = sessions.get(clientId);
        if (session != null) {
            session.setLastHeartbeatTimestamp(System.currentTimeMillis());
        }
    }

    public void pushConfigChange(String dataId, String group, String namespace,
                                  com.google.protobuf.ProtocolStringList changedItemsList) {
        // 遍历所有订阅了该配置的客户端，推送变更
        for (ClientSession session : sessions.values()) {
            if (session.getSubscribedDataIds().contains(dataId) &&
                    session.getNamespace().equals(namespace)) {
                pushToClient(session, dataId, group, namespace, changedItemsList);
            }
        }
    }

    private void pushToClient(ClientSession session, String dataId, String group,
                               String namespace, com.google.protobuf.ProtocolStringList changedItemsList) {
        StreamObserver<SubscribeResponse> observer = session.getResponseObserver();
        if (observer == null) {
            log.warn("客户端 {} 的响应流已关闭，无法推送配置变更", session.getClientId());
            return;
        }

        try {
            SubscribeResponse response = SubscribeResponse.newBuilder()
                    .setRequestId(generateRequestId())
                    .setDataId(dataId)
                    .setGroup(group)
                    .addAllChangedItems(null) // 会在调用处填充变更项
                    .setVersion(System.currentTimeMillis())
                    .setStatus(com.configcenter.protocol.ResponseStatus.SUCCESS)
                    .setTimestamp(System.currentTimeMillis())
                    .build();

            observer.onNext(response);
            log.debug("配置变更已推送到客户端 {}, dataId: {}", session.getClientId(), dataId);
        } catch (Exception e) {
            log.error("推送配置变更失败, clientId: {}, dataId: {}", session.getClientId(), dataId, e);
            unregisterSession(session.getClientId());
        }
    }

    public int getSessionCount() {
        return sessions.size();
    }

    public Map<String, ClientSession> getAllSessions() {
        return new ConcurrentHashMap<>(sessions);
    }

    private String generateRequestId() {
        return "REQ-" + System.currentTimeMillis() + "-" + (int)(Math.random() * 1000);
    }
}

package com.configcenter.server.grpc;

import com.configcenter.protocol.*;
import com.configcenter.server.model.ClientSession;
import com.configcenter.server.service.ClientSessionManager;
import com.configcenter.server.service.ConfigChangeDetector;
import com.configcenter.server.service.NacosConfigListener;
import io.grpc.stub.StreamObserver;
import lombok.extern.slf4j.Slf4j;
import net.devh.boot.grpc.server.service.GrpcService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@GrpcService
public class ConfigGrpcService extends ConfigServiceGrpc.ConfigServiceImplBase {

    @Autowired
    private NacosConfigListener nacosConfigListener;

    @Autowired
    private ClientSessionManager clientSessionManager;

    @Autowired
    private ConfigChangeDetector configChangeDetector;

    @Value("${spring.cloud.nacos.config.namespace:public}")
    private String namespace;

    @Override
    public void subscribe(SubscribeRequest request, StreamObserver<SubscribeResponse> responseObserver) {
        ClientInfo clientInfo = request.getClient();
        String clientId = clientInfo.getClientId();
        
        if (clientId == null || clientId.isEmpty()) {
            clientId = generateClientId();
        }

        // 创建客户端会话
        ClientSession session = ClientSession.builder()
                .clientId(clientId)
                .serviceName(clientInfo.getServiceName())
                .group(clientInfo.getGroup())
                .namespace(clientInfo.getNamespace().isEmpty() ? namespace : clientInfo.getNamespace())
                .subscribedDataIds(new HashSet<>(request.getDataIdsList()))
                .knownVersions(request.getKnownVersionsMap())
                .responseObserver(responseObserver)
                .connectedTimestamp(System.currentTimeMillis())
                .lastHeartbeatTimestamp(System.currentTimeMillis())
                .metadata(clientInfo.getMetadataMap())
                .build();

        // 注册会话
        clientSessionManager.registerSession(session);

        // 为每个订阅的配置添加Nacos监听器
        for (String dataId : request.getDataIdsList()) {
            String group = clientInfo.getGroup().isEmpty() ? "DEFAULT_GROUP" : clientInfo.getGroup();
            nacosConfigListener.addConfigListener(dataId, group);

            // 首次推送全量配置
            sendFullConfig(session, dataId, group);
        }

        // 监听流关闭
        responseObserver.setOnReadyHandler(() -> 
            log.debug("客户端 {} 订阅流已就绪", clientId));

        // 监听流取消
        responseObserver.setOnCancelHandler(() -> {
            log.info("客户端 {} 取消订阅", clientId);
            clientSessionManager.unregisterSession(clientId);
        });

        log.info("客户端 {} 订阅成功, 订阅配置数: {}", clientId, request.getDataIdsCount());
    }

    private void sendFullConfig(ClientSession session, String dataId, String group) {
        try {
            Map<String, String> configMap = nacosConfigListener.getConfigMap(dataId, group);
            if (configMap.isEmpty()) {
                return;
            }

            List<ConfigItem> items = new java.util.ArrayList<>();
            for (Map.Entry<String, String> entry : configMap.entrySet()) {
                items.add(ConfigItem.newBuilder()
                        .setKey(entry.getKey())
                        .setValue(entry.getValue())
                        .setChangeType(ConfigChangeType.ADDED)
                        .setVersion(System.currentTimeMillis())
                        .build());
            }

            SubscribeResponse response = SubscribeResponse.newBuilder()
                    .setRequestId(generateRequestId())
                    .setDataId(dataId)
                    .setGroup(group)
                    .addAllChangedItems(items)
                    .setVersion(configChangeDetector.getCurrentVersion(dataId, group, namespace))
                    .setStatus(ResponseStatus.SUCCESS)
                    .setTimestamp(System.currentTimeMillis())
                    .build();

            session.getResponseObserver().onNext(response);
            log.debug("首次全量配置推送成功, clientId: {}, dataId: {}, 配置数: {}",
                    session.getClientId(), dataId, items.size());
        } catch (Exception e) {
            log.error("首次全量配置推送失败, clientId: {}, dataId: {}", session.getClientId(), dataId, e);
        }
    }

    @Override
    public void pullConfig(PullConfigRequest request, StreamObserver<PullConfigResponse> responseObserver) {
        String dataId = request.getDataId();
        String group = request.getGroup().isEmpty() ? "DEFAULT_GROUP" : request.getGroup();
        String clientNamespace = request.getClient().getNamespace().isEmpty() ? namespace : request.getClient().getNamespace();

        log.info("客户端拉取配置, clientId: {}, dataId: {}, group: {}",
                request.getClient().getClientId(), dataId, group);

        try {
            Map<String, String> configMap = nacosConfigListener.getConfigMap(dataId, group);
            long currentVersion = configChangeDetector.getCurrentVersion(dataId, group, clientNamespace);

            PullConfigResponse.Builder builder = PullConfigResponse.newBuilder()
                    .setRequestId(generateRequestId())
                    .setDataId(dataId)
                    .setGroup(group)
                    .setVersion(currentVersion)
                    .setTimestamp(System.currentTimeMillis());

            if (request.getFullPull()) {
                // 全量拉取
                builder.putAllConfigData(configMap);
                builder.setStatus(ResponseStatus.SUCCESS);
            } else {
                // 增量拉取，检查版本号
                if (request.getKnownVersion() < currentVersion) {
                    List<ConfigItem> changes = configChangeDetector.detectChanges(
                            dataId, group, clientNamespace, configMap);
                    builder.addAllChangedItems(changes);
                    builder.setStatus(ResponseStatus.SUCCESS);
                } else {
                    builder.setStatus(ResponseStatus.NO_CHANGE);
                    builder.setMessage("配置无变更");
                }
            }

            responseObserver.onNext(builder.build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            log.error("拉取配置失败, dataId: {}, group: {}", dataId, group, e);
            responseObserver.onNext(PullConfigResponse.newBuilder()
                    .setRequestId(generateRequestId())
                    .setDataId(dataId)
                    .setGroup(group)
                    .setStatus(ResponseStatus.ERROR)
                    .setMessage(e.getMessage())
                    .setTimestamp(System.currentTimeMillis())
                    .build());
            responseObserver.onCompleted();
        }
    }

    @Override
    public StreamObserver<HeartbeatRequest> heartbeat(StreamObserver<HeartbeatResponse> responseObserver) {
        return new StreamObserver<HeartbeatRequest>() {
            private String currentClientId;

            @Override
            public void onNext(HeartbeatRequest request) {
                currentClientId = request.getClientId();
                clientSessionManager.updateHeartbeat(currentClientId);

                HeartbeatResponse response = HeartbeatResponse.newBuilder()
                        .setServerId("config-server")
                        .setTimestamp(System.currentTimeMillis())
                        .setAccepted(true)
                        .setNextHeartbeatInterval(30000) // 30秒
                        .build();

                responseObserver.onNext(response);
            }

            @Override
            public void onError(Throwable t) {
                log.warn("客户端 {} 心跳连接异常, message: {}", currentClientId, t.getMessage());
                if (currentClientId != null) {
                    clientSessionManager.unregisterSession(currentClientId);
                }
            }

            @Override
            public void onCompleted() {
                log.info("客户端 {} 心跳连接关闭", currentClientId);
                if (currentClientId != null) {
                    clientSessionManager.unregisterSession(currentClientId);
                }
                responseObserver.onCompleted();
            }
        };
    }

    private String generateClientId() {
        return "client-" + UUID.randomUUID().toString().substring(0, 8);
    }

    private String generateRequestId() {
        return "REQ-" + System.currentTimeMillis() + "-" + (int)(Math.random() * 1000);
    }
}

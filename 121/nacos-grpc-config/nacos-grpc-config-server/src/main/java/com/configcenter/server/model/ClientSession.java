package com.configcenter.server.model;

import com.configcenter.protocol.SubscribeResponse;
import io.grpc.stub.StreamObserver;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ClientSession {
    private String clientId;
    private String serviceName;
    private String group;
    private String namespace;
    private Set<String> subscribedDataIds = new HashSet<>();
    private Map<String, Long> knownVersions = new ConcurrentHashMap<>();
    private StreamObserver<SubscribeResponse> responseObserver;
    private long connectedTimestamp;
    private long lastHeartbeatTimestamp;
    private Map<String, String> metadata;
    private String clientIp;
}

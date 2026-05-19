package com.scheduler.raft;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ClusterManager {

    @Resource
    private RaftNode raftNode;

    @Value("${raft.node-id}")
    private String nodeId;

    @Value("${server.port}")
    private int serverPort;

    @Value("${raft.peer-nodes:}")
    private String peerNodes;

    private final RestTemplate restTemplate = new RestTemplate();

    @PostConstruct
    public void init() {
        if (peerNodes != null && !peerNodes.trim().isEmpty()) {
            String[] peers = peerNodes.split(",");
            for (String peer : peers) {
                String[] parts = peer.split(":");
                if (parts.length >= 2) {
                    String peerId = parts[0];
                    String peerAddress = parts[1] + ":" + (parts.length > 2 ? parts[2] : "8080");
                    raftNode.addPeer(peerId, peerAddress);
                }
            }
        }
        log.info("集群管理器初始化完成，初始节点数: {}", raftNode.getPeerIds().size());
    }

    public RaftMessage.ClusterJoinResponse handleJoinRequest(RaftMessage.ClusterJoinRequest request) {
        RaftMessage.ClusterJoinResponse response = new RaftMessage.ClusterJoinResponse();

        if (raftNode.isLeader()) {
            raftNode.addPeer(request.getNodeId(), request.getAddress());
            response.setSuccess(true);
            response.setMessage("加入集群成功");
            response.setLeaderId(nodeId);
            response.setPeers(new ArrayList<>(raftNode.getPeerIds()));
            log.info("节点 {} 加入集群，地址: {}", request.getNodeId(), request.getAddress());
        } else {
            String leaderAddress = raftNode.getLeaderAddress();
            if (leaderAddress != null) {
                response.setSuccess(false);
                response.setMessage("请向Leader节点发起加入请求");
                response.setLeaderId(raftNode.getCurrentLeader());
            } else {
                response.setSuccess(false);
                response.setMessage("集群正在选举中，请稍后重试");
            }
        }

        return response;
    }

    public boolean joinCluster(String bootstrapAddress) {
        try {
            String url = "http://" + bootstrapAddress + "/api/cluster/join";
            RaftMessage.ClusterJoinRequest request = new RaftMessage.ClusterJoinRequest();
            request.setNodeId(nodeId);
            request.setAddress("localhost:" + serverPort);

            ResponseEntity<RaftMessage.ClusterJoinResponse> responseEntity =
                    restTemplate.postForEntity(url, request, RaftMessage.ClusterJoinResponse.class);

            RaftMessage.ClusterJoinResponse response = responseEntity.getBody();
            if (response != null && response.isSuccess()) {
                log.info("成功加入集群，Leader: {}", response.getLeaderId());
                for (String peerId : response.getPeers()) {
                    if (!peerId.equals(nodeId)) {
                        raftNode.addPeer(peerId, bootstrapAddress);
                    }
                }
                return true;
            } else {
                log.warn("加入集群失败: {}", response != null ? response.getMessage() : "未知错误");
                return false;
            }
        } catch (Exception e) {
            log.error("加入集群失败", e);
            return false;
        }
    }

    public void leaveCluster() {
        log.info("节点 {} 离开集群", nodeId);
        raftNode.shutdown();
    }

    public List<Map<String, String>> getClusterMembers() {
        List<Map<String, String>> members = new ArrayList<>();

        Map<String, String> self = raftNode.getClusterInfo();
        self.put("isLocal", "true");
        members.add(self);

        for (String peerId : raftNode.getPeerIds()) {
            Map<String, String> peer = new java.util.HashMap<>();
            peer.put("nodeId", peerId);
            peer.put("address", raftNode.getPeerAddresses().getOrDefault(peerId, ""));
            peer.put("isLocal", "false");
            members.add(peer);
        }

        return members;
    }

    public boolean isLeader() {
        return raftNode.isLeader();
    }

    public String getCurrentLeader() {
        return raftNode.getCurrentLeader();
    }
}

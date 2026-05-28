package com.datasync.coordinator;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.monitor.LagDetector;
import com.datasync.common.util.IdGenerator;
import com.datasync.common.util.JsonUtils;
import com.datasync.coordinator.model.LinkInfo;
import com.datasync.coordinator.model.NodeInfo;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.zookeeper.*;
import org.apache.zookeeper.data.Stat;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

@Slf4j
public class ZookeeperCoordinator {
    private final String connectString;
    private final int sessionTimeout;
    private final String nodeId;
    private final String datacenterId;

    private ZooKeeper zkClient;
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final AtomicBoolean isLeader = new AtomicBoolean(false);
    private final Map<String, NodeInfo> activeNodes = new ConcurrentHashMap<>();
    private final Map<String, LinkInfo> activeLinks = new ConcurrentHashMap<>();
    private ExecutorService heartbeatExecutor;
    private LagDetector lagDetector;

    private Consumer<LeaderChangeEvent> leaderChangeListener;
    private Consumer<NodeChangeEvent> nodeChangeListener;
    private Consumer<LinkChangeEvent> linkChangeListener;

    @Builder
    public ZookeeperCoordinator(String connectString,
                                int sessionTimeout,
                                String nodeId,
                                String datacenterId) {
        this.connectString = connectString;
        this.sessionTimeout = sessionTimeout > 0 ? sessionTimeout : SyncConstants.SESSION_TIMEOUT_MS;
        this.nodeId = nodeId != null ? nodeId : IdGenerator.generateMessageId("NODE");
        this.datacenterId = datacenterId;
    }

    public void setLagDetector(LagDetector lagDetector) {
        this.lagDetector = lagDetector;
    }

    public void start() throws IOException {
        log.info("Starting ZooKeeper coordinator: nodeId={}, datacenterId={}", nodeId, datacenterId);

        zkClient = new ZooKeeper(connectString, sessionTimeout, this::processWatcherEvent);
        waitForConnection();

        initializeZkPaths();
        registerNode();
        startHeartbeat();
        tryLeadership();
        watchNodes();
        watchLinks();

        log.info("ZooKeeper coordinator started: nodeId={}", nodeId);
    }

    public void stop() {
        log.info("Stopping ZooKeeper coordinator: nodeId={}", nodeId);
        if (heartbeatExecutor != null) {
            heartbeatExecutor.shutdownNow();
        }
        try {
            if (zkClient != null) {
                zkClient.close();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        connected.set(false);
        log.info("ZooKeeper coordinator stopped: nodeId={}", nodeId);
    }

    private void waitForConnection() {
        long start = System.currentTimeMillis();
        while (!connected.get()) {
            if (System.currentTimeMillis() - start > sessionTimeout) {
                throw new RuntimeException("Timeout waiting for ZooKeeper connection");
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void processWatcherEvent(WatchedEvent event) {
        log.debug("ZooKeeper event: type={}, state={}, path={}", event.getType(), event.getState(), event.getPath());

        if (event.getState() == Watcher.Event.KeeperState.SyncConnected) {
            connected.set(true);
        } else if (event.getState() == Watcher.Event.KeeperState.Disconnected) {
            connected.set(false);
        } else if (event.getState() == Watcher.Event.KeeperState.Expired) {
            connected.set(false);
            log.warn("ZooKeeper session expired, attempting reconnection");
            reconnect();
        }

        if (event.getType() == Watcher.Event.EventType.NodeChildrenChanged) {
            if (event.getPath().equals(SyncConstants.ZK_NODES_PATH)) {
                handleNodeChange();
            } else if (event.getPath().equals(SyncConstants.ZK_TOPOLOGY_PATH)) {
                handleLinkChange();
            }
        } else if (event.getType() == Watcher.Event.EventType.NodeDeleted) {
            if (event.getPath().startsWith(SyncConstants.ZK_LEADER_PATH)) {
                handleLeaderLost();
            }
        }
    }

    private void reconnect() {
        try {
            if (zkClient != null) {
                zkClient.close();
            }
            zkClient = new ZooKeeper(connectString, sessionTimeout, this::processWatcherEvent);
            waitForConnection();
            registerNode();
            tryLeadership();
        } catch (Exception e) {
            log.error("Failed to reconnect to ZooKeeper", e);
        }
    }

    private void initializeZkPaths() {
        try {
            createPathIfNotExists(SyncConstants.ZK_ROOT_PATH);
            createPathIfNotExists(SyncConstants.ZK_NODES_PATH);
            createPathIfNotExists(SyncConstants.ZK_LEADER_PATH);
            createPathIfNotExists(SyncConstants.ZK_CONFIG_PATH);
            createPathIfNotExists(SyncConstants.ZK_TOPOLOGY_PATH);
            createPathIfNotExists(SyncConstants.ZK_HEARTBEAT_PATH);
        } catch (Exception e) {
            log.error("Failed to initialize ZooKeeper paths", e);
        }
    }

    private void createPathIfNotExists(String path) throws KeeperException, InterruptedException {
        Stat stat = zkClient.exists(path, false);
        if (stat == null) {
            zkClient.create(path, new byte[0], ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.PERSISTENT);
            log.debug("Created ZooKeeper path: {}", path);
        }
    }

    private void registerNode() {
        try {
            String nodePath = SyncConstants.ZK_NODES_PATH + "/" + nodeId;
            NodeInfo nodeInfo = NodeInfo.builder()
                    .nodeId(nodeId)
                    .datacenterId(datacenterId)
                    .startTime(System.currentTimeMillis())
                    .status("ACTIVE")
                    .build();

            byte[] data = JsonUtils.toJsonBytes(nodeInfo);
            zkClient.create(nodePath, data, ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.EPHEMERAL);
            log.info("Registered node: {}", nodeId);
        } catch (Exception e) {
            log.error("Failed to register node: {}", nodeId, e);
        }
    }

    private void startHeartbeat() {
        heartbeatExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "zk-heartbeat-" + nodeId);
            t.setDaemon(true);
            return t;
        });

        heartbeatExecutor.submit(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    String heartbeatPath = SyncConstants.ZK_HEARTBEAT_PATH + "/" + nodeId;
                    Map<String, Object> heartbeat = new HashMap<>();
                    heartbeat.put("nodeId", nodeId);
                    heartbeat.put("timestamp", System.currentTimeMillis());

                    Stat stat = zkClient.exists(heartbeatPath, false);
                    byte[] data = JsonUtils.toJsonBytes(heartbeat);
                    if (stat == null) {
                        zkClient.create(heartbeatPath, data, ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.EPHEMERAL);
                    } else {
                        zkClient.setData(heartbeatPath, data, stat.getVersion());
                    }

                    Thread.sleep(SyncConstants.HEARTBEAT_INTERVAL_MS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("Heartbeat update failed", e);
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        });
    }

    private void tryLeadership() {
        try {
            String leaderPath = SyncConstants.ZK_LEADER_PATH + "/" + nodeId;
            zkClient.create(leaderPath, new byte[0], ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.EPHEMERAL);
            isLeader.set(true);
            log.info("This node is now the leader: {}", nodeId);
            notifyLeaderChange(true);
        } catch (KeeperException.NodeExistsException e) {
            isLeader.set(false);
            log.debug("Another node is already the leader");
            watchLeader();
        } catch (Exception e) {
            log.error("Failed to try leadership", e);
        }
    }

    private void watchLeader() {
        try {
            List<String> children = zkClient.getChildren(SyncConstants.ZK_LEADER_PATH, true);
            if (children.isEmpty()) {
                tryLeadership();
            }
        } catch (Exception e) {
            log.error("Failed to watch leader", e);
        }
    }

    private void handleLeaderLost() {
        isLeader.set(false);
        log.info("Lost leadership, attempting to become leader");
        notifyLeaderChange(false);
        tryLeadership();
    }

    private void watchNodes() {
        try {
            zkClient.getChildren(SyncConstants.ZK_NODES_PATH, true);
            refreshNodes();
        } catch (Exception e) {
            log.error("Failed to watch nodes", e);
        }
    }

    private void handleNodeChange() {
        log.info("Node change detected");
        refreshNodes();
        watchNodes();
    }

    private void refreshNodes() {
        try {
            List<String> children = zkClient.getChildren(SyncConstants.ZK_NODES_PATH, false);
            Set<String> currentNodes = new HashSet<>(activeNodes.keySet());

            for (String child : children) {
                if (!currentNodes.contains(child)) {
                    String nodePath = SyncConstants.ZK_NODES_PATH + "/" + child;
                    byte[] data = zkClient.getData(nodePath, false, null);
                    NodeInfo nodeInfo = JsonUtils.fromJsonBytes(data, NodeInfo.class);
                    if (nodeInfo != null) {
                        activeNodes.put(child, nodeInfo);
                        notifyNodeChange(nodeInfo, true);
                    }
                }
                currentNodes.remove(child);
            }

            for (String removedNode : currentNodes) {
                NodeInfo removed = activeNodes.remove(removedNode);
                if (removed != null) {
                    notifyNodeChange(removed, false);
                }
            }
        } catch (Exception e) {
            log.error("Failed to refresh nodes", e);
        }
    }

    private void watchLinks() {
        try {
            zkClient.getChildren(SyncConstants.ZK_TOPOLOGY_PATH, true);
            refreshLinks();
        } catch (Exception e) {
            log.error("Failed to watch links", e);
        }
    }

    private void handleLinkChange() {
        log.info("Link change detected");
        refreshLinks();
        watchLinks();
    }

    private void refreshLinks() {
        try {
            List<String> children = zkClient.getChildren(SyncConstants.ZK_TOPOLOGY_PATH, false);
            Set<String> currentLinks = new HashSet<>(activeLinks.keySet());

            for (String child : children) {
                if (!currentLinks.contains(child)) {
                    String linkPath = SyncConstants.ZK_TOPOLOGY_PATH + "/" + child;
                    byte[] data = zkClient.getData(linkPath, false, null);
                    LinkInfo linkInfo = JsonUtils.fromJsonBytes(data, LinkInfo.class);
                    if (linkInfo != null) {
                        activeLinks.put(child, linkInfo);
                        notifyLinkChange(linkInfo, true);
                    }
                }
                currentLinks.remove(child);
            }

            for (String removedLink : currentLinks) {
                LinkInfo removed = activeLinks.remove(removedLink);
                if (removed != null) {
                    notifyLinkChange(removed, false);
                }
            }
        } catch (Exception e) {
            log.error("Failed to refresh links", e);
        }
    }

    public void registerLink(LinkInfo linkInfo) {
        if (!isLeader.get()) {
            log.warn("Only leader can register links");
            return;
        }
        try {
            String linkPath = SyncConstants.ZK_TOPOLOGY_PATH + "/" + linkInfo.getLinkId();
            byte[] data = JsonUtils.toJsonBytes(linkInfo);
            Stat stat = zkClient.exists(linkPath, false);
            if (stat == null) {
                zkClient.create(linkPath, data, ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.PERSISTENT);
                log.info("Registered link: {}", linkInfo.getLinkId());
            } else {
                zkClient.setData(linkPath, data, stat.getVersion());
                log.info("Updated link: {}", linkInfo.getLinkId());
            }
        } catch (Exception e) {
            log.error("Failed to register link", e);
        }
    }

    public void switchLink(String linkId, boolean activate) {
        switchLink(linkId, activate, 60000);
    }

    public void switchLink(String linkId, boolean activate, long lagWaitTimeoutMs) {
        if (!isLeader.get()) {
            log.warn("Only leader can switch links");
            return;
        }

        if (activate && lagDetector != null) {
            try {
                log.info("Checking lag before activating link: {}", linkId);
                lagDetector.waitForLagBelowThreshold(lagWaitTimeoutMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Interrupted while waiting for lag to drop, link: {}", linkId);
                return;
            }

            if (!lagDetector.isLagSafeForSwitch()) {
                LagDetector.LagStatus status = lagDetector.getLagStatus();
                log.error("Lag still too high after waiting, aborting link switch: linkId={}, totalLag={}, threshold={}",
                        linkId, status.getTotalLag(), status.getLowWatermarkThreshold());
                throw new IllegalStateException("Lag too high for switch: " + status.getTotalLag());
            }
            log.info("Lag check passed for link switch: linkId={}", linkId);
        }

        try {
            String linkPath = SyncConstants.ZK_TOPOLOGY_PATH + "/" + linkId;
            byte[] data = zkClient.getData(linkPath, false, null);
            LinkInfo linkInfo = JsonUtils.fromJsonBytes(data, LinkInfo.class);
            if (linkInfo != null) {
                linkInfo.setActive(activate);
                linkInfo.setStatus(activate ? "ACTIVE" : "INACTIVE");
                zkClient.setData(linkPath, JsonUtils.toJsonBytes(linkInfo), -1);
                log.info("Switched link {} to {}", linkId, activate ? "ACTIVE" : "INACTIVE");
            }
        } catch (Exception e) {
            log.error("Failed to switch link", e);
        }
    }

    public void setLeaderChangeListener(Consumer<LeaderChangeEvent> listener) {
        this.leaderChangeListener = listener;
    }

    public void setNodeChangeListener(Consumer<NodeChangeEvent> listener) {
        this.nodeChangeListener = listener;
    }

    public void setLinkChangeListener(Consumer<LinkChangeEvent> listener) {
        this.linkChangeListener = listener;
    }

    private void notifyLeaderChange(boolean isLeaderNow) {
        if (leaderChangeListener != null) {
            leaderChangeListener.accept(new LeaderChangeEvent(nodeId, isLeaderNow));
        }
    }

    private void notifyNodeChange(NodeInfo nodeInfo, boolean added) {
        if (nodeChangeListener != null) {
            nodeChangeListener.accept(new NodeChangeEvent(nodeInfo, added));
        }
    }

    private void notifyLinkChange(LinkInfo linkInfo, boolean added) {
        if (linkChangeListener != null) {
            linkChangeListener.accept(new LinkChangeEvent(linkInfo, added));
        }
    }

    public boolean isConnected() {
        return connected.get();
    }

    public boolean isLeader() {
        return isLeader.get();
    }

    public String getNodeId() {
        return nodeId;
    }

    public String getDatacenterId() {
        return datacenterId;
    }

    public Map<String, NodeInfo> getActiveNodes() {
        return new HashMap<>(activeNodes);
    }

    public Map<String, LinkInfo> getActiveLinks() {
        return new HashMap<>(activeLinks);
    }

    @Data
    public static class LeaderChangeEvent {
        private final String nodeId;
        private final boolean isLeader;

        public LeaderChangeEvent(String nodeId, boolean isLeader) {
            this.nodeId = nodeId;
            this.isLeader = isLeader;
        }
    }

    @Data
    public static class NodeChangeEvent {
        private final NodeInfo nodeInfo;
        private final boolean added;

        public NodeChangeEvent(NodeInfo nodeInfo, boolean added) {
            this.nodeInfo = nodeInfo;
            this.added = added;
        }
    }

    @Data
    public static class LinkChangeEvent {
        private final LinkInfo linkInfo;
        private final boolean added;

        public LinkChangeEvent(LinkInfo linkInfo, boolean added) {
            this.linkInfo = linkInfo;
            this.added = added;
        }
    }
}

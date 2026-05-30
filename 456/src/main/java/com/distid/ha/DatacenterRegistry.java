package com.distid.ha;

import lombok.extern.slf4j.Slf4j;
import org.apache.curator.framework.CuratorFramework;
import org.apache.zookeeper.CreateMode;
import org.apache.zookeeper.KeeperException;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Slf4j
public class DatacenterRegistry {

    private static final String DC_REGISTRY_PATH = "/distid-ha/datacenters";
    private static final String DC_FAILOVER_PATH = "/distid-ha/failover";
    private static final long HEARTBEAT_INTERVAL_MS = 5000;

    private final CuratorFramework curator;
    private final String localDcCode;
    private final String localRegion;
    private final int localPriority;
    private final long segmentOffset;
    private final long segmentStep;

    private volatile DatacenterNode.Status localStatus = DatacenterNode.Status.ACTIVE;
    private volatile Map<String, DatacenterNode> remoteDatacenters = new HashMap<>();
    private volatile boolean running = true;

    public DatacenterRegistry(CuratorFramework curator, String localDcCode, String localRegion,
                               int localPriority, long segmentOffset, long segmentStep) {
        this.curator = curator;
        this.localDcCode = localDcCode;
        this.localRegion = localRegion;
        this.localPriority = localPriority;
        this.segmentOffset = segmentOffset;
        this.segmentStep = segmentStep;
    }

    @PostConstruct
    public void init() throws Exception {
        ensurePathExists(DC_REGISTRY_PATH);
        ensurePathExists(DC_FAILOVER_PATH);
        registerLocalDc();
        startHeartbeat();
        startRemoteSync();
        log.info("DatacenterRegistry initialized: dcCode={}, region={}, priority={}, offset={}, step={}",
                localDcCode, localRegion, localPriority, segmentOffset, segmentStep);
    }

    private void registerLocalDc() throws Exception {
        String path = DC_REGISTRY_PATH + "/" + localDcCode;
        String data = encodeDcNode();
        try {
            curator.create()
                    .orSetData()
                    .creatingParentsIfNeeded()
                    .withMode(CreateMode.EPHEMERAL)
                    .forPath(path, data.getBytes(StandardCharsets.UTF_8));
        } catch (KeeperException.NodeExistsException e) {
            curator.setData().forPath(path, data.getBytes(StandardCharsets.UTF_8));
        }
    }

    private String encodeDcNode() {
        return localDcCode + "|" + localRegion + "|" + localStatus.name() + "|"
                + localPriority + "|" + segmentOffset + "|" + segmentStep + "|" + System.currentTimeMillis();
    }

    private DatacenterNode decodeDcNode(String dcCode, byte[] data) {
        String value = new String(data, StandardCharsets.UTF_8);
        String[] parts = value.split("\\|");
        return DatacenterNode.builder()
                .dcCode(parts[0])
                .region(parts.length > 1 ? parts[1] : "")
                .status(parts.length > 2 ? DatacenterNode.Status.valueOf(parts[2]) : DatacenterNode.Status.OFFLINE)
                .priority(parts.length > 3 ? Integer.parseInt(parts[3]) : 0)
                .segmentOffset(parts.length > 4 ? Long.parseLong(parts[4]) : 0)
                .segmentStep(parts.length > 5 ? Long.parseLong(parts[5]) : 0)
                .lastHeartbeat(parts.length > 6 ? Long.parseLong(parts[6]) : 0)
                .build();
    }

    private void startHeartbeat() {
        Thread heartbeatThread = new Thread(() -> {
            while (running) {
                try {
                    Thread.sleep(HEARTBEAT_INTERVAL_MS);
                    String path = DC_REGISTRY_PATH + "/" + localDcCode;
                    curator.setData().forPath(path, encodeDcNode().getBytes(StandardCharsets.UTF_8));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.warn("DC heartbeat failed for dcCode={}", localDcCode, e);
                    tryReconnect();
                }
            }
        }, "dc-heartbeat-" + localDcCode);
        heartbeatThread.setDaemon(true);
        heartbeatThread.start();
    }

    private void startRemoteSync() {
        Thread syncThread = new Thread(() -> {
            while (running) {
                try {
                    Thread.sleep(10000);
                    refreshRemoteDatacenters();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.warn("Remote DC sync failed", e);
                }
            }
        }, "dc-remote-sync");
        syncThread.setDaemon(true);
        syncThread.start();
    }

    private void refreshRemoteDatacenters() {
        try {
            List<String> children = curator.getChildren().forPath(DC_REGISTRY_PATH);
            Map<String, DatacenterNode> updated = new HashMap<>();
            for (String dcCode : children) {
                if (dcCode.equals(localDcCode)) continue;
                try {
                    byte[] data = curator.getData().forPath(DC_REGISTRY_PATH + "/" + dcCode);
                    DatacenterNode node = decodeDcNode(dcCode, data);
                    long age = System.currentTimeMillis() - node.getLastHeartbeat();
                    if (age > 30000) {
                        log.warn("DC {} heartbeat stale ({}ms), marking OFFLINE", dcCode, age);
                    } else {
                        updated.put(dcCode, node);
                    }
                } catch (KeeperException.NoNodeException ignored) {
                } catch (Exception e) {
                    log.warn("Failed to read DC node: {}", dcCode, e);
                }
            }
            remoteDatacenters = updated;
        } catch (Exception e) {
            log.warn("Failed to refresh remote DCs", e);
        }
    }

    private void tryReconnect() {
        try {
            registerLocalDc();
        } catch (Exception e) {
            log.error("Failed to reconnect local DC node", e);
        }
    }

    private void ensurePathExists(String path) throws Exception {
        try {
            if (curator.checkExists().forPath(path) == null) {
                curator.create().creatingParentsIfNeeded().forPath(path);
            }
        } catch (KeeperException.NodeExistsException ignored) {
        }
    }

    public String getLocalDcCode() {
        return localDcCode;
    }

    public DatacenterNode.Status getLocalStatus() {
        return localStatus;
    }

    public void setLocalStatus(DatacenterNode.Status status) {
        this.localStatus = status;
        try {
            registerLocalDc();
        } catch (Exception e) {
            log.error("Failed to update local DC status to {}", status, e);
        }
    }

    public long getSegmentOffset() {
        return segmentOffset;
    }

    public long getSegmentStep() {
        return segmentStep;
    }

    public Collection<DatacenterNode> getRemoteDatacenters() {
        return remoteDatacenters.values();
    }

    public Optional<DatacenterNode> findFailoverTarget() {
        return remoteDatacenters.values().stream()
                .filter(DatacenterNode::isAvailable)
                .filter(dc -> dc.getStatus() == DatacenterNode.Status.ACTIVE || dc.getStatus() == DatacenterNode.Status.STANDBY)
                .min(Comparator.comparingInt(DatacenterNode::getPriority));
    }

    public boolean isLocalActive() {
        return localStatus == DatacenterNode.Status.ACTIVE;
    }

    @PreDestroy
    public void shutdown() {
        running = false;
        try {
            curator.delete().forPath(DC_REGISTRY_PATH + "/" + localDcCode);
        } catch (Exception e) {
            log.warn("Failed to cleanup DC node on shutdown", e);
        }
    }
}

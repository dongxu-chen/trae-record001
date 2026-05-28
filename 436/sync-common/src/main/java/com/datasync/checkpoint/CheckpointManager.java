package com.datasync.checkpoint;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.util.JsonUtils;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;
import org.apache.zookeeper.*;
import org.apache.zookeeper.data.Stat;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
public class CheckpointManager {
    private final String zkConnectString;
    private final int sessionTimeout;
    private final String nodeId;
    private final String datacenterId;
    private final long checkpointIntervalSeconds;
    private final String zkBasePath;

    private ZooKeeper zkClient;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final Map<String, Checkpoint> currentCheckpoints = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> processedCounts = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> failedCounts = new ConcurrentHashMap<>();
    private ScheduledExecutorService checkpointScheduler;
    private final Object lock = new Object();

    @Builder
    public CheckpointManager(String zkConnectString,
                             int sessionTimeout,
                             String nodeId,
                             String datacenterId,
                             long checkpointIntervalSeconds) {
        this.zkConnectString = zkConnectString;
        this.sessionTimeout = sessionTimeout > 0 ? sessionTimeout : SyncConstants.SESSION_TIMEOUT_MS;
        this.nodeId = nodeId;
        this.datacenterId = datacenterId;
        this.checkpointIntervalSeconds = checkpointIntervalSeconds > 0 ? checkpointIntervalSeconds : 30;
        this.zkBasePath = SyncConstants.ZK_ROOT_PATH + "/checkpoints/" + datacenterId + "/" + nodeId;
    }

    public void start() throws Exception {
        if (running.compareAndSet(false, true)) {
            log.info("Starting Checkpoint Manager for node: {}, datacenter: {}", nodeId, datacenterId);

            zkClient = new ZooKeeper(zkConnectString, sessionTimeout, this::processWatcher);
            waitForConnection();
            initializeZkPaths();

            checkpointScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "checkpoint-scheduler");
                t.setDaemon(true);
                return t;
            });

            checkpointScheduler.scheduleAtFixedRate(
                    this::saveCheckpoints,
                    checkpointIntervalSeconds,
                    checkpointIntervalSeconds,
                    TimeUnit.SECONDS
            );

            log.info("Checkpoint Manager started, interval: {} seconds", checkpointIntervalSeconds);
        }
    }

    public void stop() {
        if (running.compareAndSet(true, false)) {
            log.info("Stopping Checkpoint Manager");

            try {
                saveCheckpoints();
            } catch (Exception e) {
                log.error("Error saving final checkpoints", e);
            }

            if (checkpointScheduler != null) {
                checkpointScheduler.shutdown();
                try {
                    if (!checkpointScheduler.awaitTermination(10, TimeUnit.SECONDS)) {
                        checkpointScheduler.shutdownNow();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }

            if (zkClient != null) {
                try {
                    zkClient.close();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }

            log.info("Checkpoint Manager stopped");
        }
    }

    private void processWatcher(WatchedEvent event) {
        if (event.getState() == Watcher.Event.KeeperState.SyncConnected) {
            log.debug("ZooKeeper connected for checkpoint manager");
        } else if (event.getState() == Watcher.Event.KeeperState.Expired) {
            log.warn("ZooKeeper session expired, attempting reconnection");
            reconnect();
        }
    }

    private void waitForConnection() throws InterruptedException {
        long start = System.currentTimeMillis();
        while (zkClient.getState() != ZooKeeper.States.CONNECTED) {
            if (System.currentTimeMillis() - start > sessionTimeout) {
                throw new RuntimeException("Timeout waiting for ZooKeeper connection");
            }
            Thread.sleep(100);
        }
    }

    private void reconnect() {
        try {
            if (zkClient != null) {
                zkClient.close();
            }
            zkClient = new ZooKeeper(zkConnectString, sessionTimeout, this::processWatcher);
            waitForConnection();
            initializeZkPaths();
        } catch (Exception e) {
            log.error("Failed to reconnect to ZooKeeper", e);
        }
    }

    private void initializeZkPaths() throws Exception {
        createPathIfNotExists(SyncConstants.ZK_ROOT_PATH + "/checkpoints");
        createPathIfNotExists(SyncConstants.ZK_ROOT_PATH + "/checkpoints/" + datacenterId);
        createPathIfNotExists(zkBasePath);
    }

    private void createPathIfNotExists(String path) throws Exception {
        Stat stat = zkClient.exists(path, false);
        if (stat == null) {
            zkClient.create(path, new byte[0], ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.PERSISTENT);
            log.debug("Created checkpoint path: {}", path);
        }
    }

    public void recordEventProcessed(String channelId, DataChangeEvent event) {
        processedCounts.computeIfAbsent(channelId, k -> new AtomicLong(0)).incrementAndGet();
        synchronized (lock) {
            Checkpoint checkpoint = currentCheckpoints.computeIfAbsent(channelId, k ->
                    Checkpoint.builder()
                            .channelId(channelId)
                            .nodeId(nodeId)
                            .datacenterId(datacenterId)
                            .tableName(event.getFullTableName())
                            .status("ACTIVE")
                            .processedEventCount(0)
                            .failedEventCount(0)
                            .build()
            );

            checkpoint.setLastEventId(event.getEventId());
            checkpoint.setLastProcessedHlcTimestamp(event.getHlcTimestamp() != null ? event.getHlcTimestamp() : System.currentTimeMillis());
            if (event.getLogicalClock() != null) {
                checkpoint.setLastProcessedLogicalClock(event.getLogicalClock());
            }
        }
    }

    public void recordEventFailed(String channelId) {
        failedCounts.computeIfAbsent(channelId, k -> new AtomicLong(0)).incrementAndGet();
    }

    public void recordOffset(String channelId, int partition, long offset) {
        synchronized (lock) {
            Checkpoint checkpoint = currentCheckpoints.computeIfAbsent(channelId, k ->
                    Checkpoint.builder()
                            .channelId(channelId)
                            .nodeId(nodeId)
                            .datacenterId(datacenterId)
                            .status("ACTIVE")
                            .partitionOffsets(new HashMap<>())
                            .processedEventCount(0)
                            .failedEventCount(0)
                            .build()
            );

            if (checkpoint.getPartitionOffsets() == null) {
                checkpoint.setPartitionOffsets(new HashMap<>());
            }
            checkpoint.getPartitionOffsets().put(partition, offset);
        }
    }

    public void saveCheckpoints() {
        if (!running.get()) return;

        synchronized (lock) {
            for (Map.Entry<String, Checkpoint> entry : currentCheckpoints.entrySet()) {
                String channelId = entry.getKey();
                Checkpoint checkpoint = entry.getValue();

                try {
                    checkpoint.setCheckpointId(channelId + "_" + System.currentTimeMillis());
                    checkpoint.setCheckpointTime(LocalDateTime.now());
                    checkpoint.setProcessedEventCount(processedCounts.getOrDefault(channelId, new AtomicLong(0)).get());
                    checkpoint.setFailedEventCount(failedCounts.getOrDefault(channelId, new AtomicLong(0)).get());

                    String path = zkBasePath + "/" + channelId;
                    byte[] data = JsonUtils.toJsonBytes(checkpoint);

                    Stat stat = zkClient.exists(path, false);
                    if (stat == null) {
                        zkClient.create(path, data, ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.PERSISTENT);
                    } else {
                        zkClient.setData(path, data, stat.getVersion());
                    }

                    log.debug("Saved checkpoint for channel: {}, processed: {}",
                            channelId, checkpoint.getProcessedEventCount());
                } catch (Exception e) {
                    log.error("Failed to save checkpoint for channel: {}", channelId, e);
                }
            }
        }
    }

    public Checkpoint loadCheckpoint(String channelId) throws Exception {
        String path = zkBasePath + "/" + channelId;
        Stat stat = zkClient.exists(path, false);
        if (stat == null) {
            log.info("No checkpoint found for channel: {}", channelId);
            return null;
        }

        byte[] data = zkClient.getData(path, false, stat);
        Checkpoint checkpoint = JsonUtils.fromJsonBytes(data, Checkpoint.class);
        log.info("Loaded checkpoint for channel: {}, processed: {}, lastEventId: {}",
                channelId, checkpoint.getProcessedEventCount(), checkpoint.getLastEventId());

        synchronized (lock) {
            currentCheckpoints.put(channelId, checkpoint);
            if (checkpoint.getProcessedEventCount() > 0) {
                processedCounts.put(channelId, new AtomicLong(checkpoint.getProcessedEventCount()));
            }
            if (checkpoint.getFailedEventCount() > 0) {
                failedCounts.put(channelId, new AtomicLong(checkpoint.getFailedEventCount()));
            }
        }

        return checkpoint;
    }

    public Map<String, Checkpoint> loadAllCheckpoints() throws Exception {
        Map<String, Checkpoint> checkpoints = new HashMap<>();
        List<String> children = zkClient.getChildren(zkBasePath, false);
        for (String child : children) {
            try {
                Checkpoint cp = loadCheckpoint(child);
                if (cp != null) {
                    checkpoints.put(child, cp);
                }
            } catch (Exception e) {
                log.error("Failed to load checkpoint: {}", child, e);
            }
        }
        return checkpoints;
    }

    public void clearCheckpoint(String channelId) throws Exception {
        String path = zkBasePath + "/" + channelId;
        Stat stat = zkClient.exists(path, false);
        if (stat != null) {
            zkClient.delete(path, stat.getVersion());
            synchronized (lock) {
                currentCheckpoints.remove(channelId);
                processedCounts.remove(channelId);
                failedCounts.remove(channelId);
            }
            log.info("Cleared checkpoint for channel: {}", channelId);
        }
    }

    public boolean hasCheckpoint(String channelId) throws Exception {
        String path = zkBasePath + "/" + channelId;
        return zkClient.exists(path, false) != null;
    }

    public Map<String, Checkpoint> getCurrentCheckpoints() {
        synchronized (lock) {
            return new HashMap<>(currentCheckpoints);
        }
    }

    public long getTotalProcessedCount() {
        return processedCounts.values().stream().mapToLong(AtomicLong::get).sum();
    }

    public long getTotalFailedCount() {
        return failedCounts.values().stream().mapToLong(AtomicLong::get).sum();
    }
}

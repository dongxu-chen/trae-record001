package com.distributed.lock.server.migration;

import com.distributed.lock.server.config.LockServerConfig;
import com.distributed.lock.server.etcd.EtcdClient;
import com.distributed.lock.server.lock.LockInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class LockMigrationManager {
    
    private static final Logger logger = LoggerFactory.getLogger(LockMigrationManager.class);
    
    private final EtcdClient etcdClient;
    private final LockServerConfig config;
    private final ConcurrentHashMap<String, LockInfo> lockRegistry;
    private final ObjectMapper objectMapper;
    private final String nodeId;
    private final ScheduledExecutorService nodeHealthChecker;
    private final Map<String, NodeInfo> clusterNodes;
    private final List<MigrationListener> migrationListeners;
    private final long nodeHealthCheckIntervalMs;
    private volatile boolean running;

    public LockMigrationManager(EtcdClient etcdClient, LockServerConfig config,
                                ConcurrentHashMap<String, LockInfo> lockRegistry, String nodeId) {
        this.etcdClient = etcdClient;
        this.config = config;
        this.lockRegistry = lockRegistry;
        this.nodeId = nodeId;
        this.objectMapper = new ObjectMapper();
        this.clusterNodes = new ConcurrentHashMap<>();
        this.migrationListeners = new ArrayList<>();
        this.nodeHealthCheckIntervalMs = 10000;
        this.nodeHealthChecker = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "node-health-checker");
            t.setDaemon(true);
            return t;
        });
        
        registerNode(nodeId);
    }

    public void addMigrationListener(MigrationListener listener) {
        migrationListeners.add(listener);
    }

    public void start() {
        if (!running) {
            running = true;
            nodeHealthChecker.scheduleAtFixedRate(
                    this::checkNodeHealth,
                    nodeHealthCheckIntervalMs,
                    nodeHealthCheckIntervalMs,
                    TimeUnit.MILLISECONDS
            );
            logger.info("Lock migration manager started for node {}", nodeId);
        }
    }

    public void stop() {
        running = false;
        nodeHealthChecker.shutdown();
        try {
            if (!nodeHealthChecker.awaitTermination(5, TimeUnit.SECONDS)) {
                nodeHealthChecker.shutdownNow();
            }
        } catch (InterruptedException e) {
            nodeHealthChecker.shutdownNow();
            Thread.currentThread().interrupt();
        }
        logger.info("Lock migration manager stopped");
    }

    public void registerNode(String nodeId) {
        NodeInfo nodeInfo = new NodeInfo(nodeId, System.currentTimeMillis());
        clusterNodes.put(nodeId, nodeInfo);
        updateNodeHeartbeat(nodeId);
    }

    public void unregisterNode(String nodeId) {
        clusterNodes.remove(nodeId);
    }

    public void updateNodeHeartbeat(String nodeId) {
        NodeInfo nodeInfo = clusterNodes.get(nodeId);
        if (nodeInfo != null) {
            nodeInfo.setLastHeartbeatMs(System.currentTimeMillis());
            nodeInfo.setHealthy(true);
        }
    }

    private void checkNodeHealth() {
        long now = System.currentTimeMillis();
        long unhealthyThreshold = nodeHealthCheckIntervalMs * 3;
        
        List<String> unhealthyNodes = new ArrayList<>();
        
        for (Map.Entry<String, NodeInfo> entry : clusterNodes.entrySet()) {
            String nodeId = entry.getKey();
            NodeInfo nodeInfo = entry.getValue();
            
            if (!nodeId.equals(this.nodeId) && nodeInfo.isHealthy()) {
                long timeSinceLastHeartbeat = now - nodeInfo.getLastHeartbeatMs();
                if (timeSinceLastHeartbeat > unhealthyThreshold) {
                    nodeInfo.setHealthy(false);
                    unhealthyNodes.add(nodeId);
                    logger.warn("Node {} detected as unhealthy (last heartbeat: {}ms ago)", 
                            nodeId, timeSinceLastHeartbeat);
                }
            }
        }
        
        for (String unhealthyNode : unhealthyNodes) {
            migrateLocksFromFailedNode(unhealthyNode);
        }
    }

    public MigrationResult migrateLocksFromFailedNode(String failedNodeId) {
        List<String> migratedLocks = new ArrayList<>();
        List<String> failedLocks = new ArrayList<>();
        
        logger.info("Starting lock migration from failed node: {}", failedNodeId);
        
        for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
            String lockName = entry.getKey();
            LockInfo lockInfo = entry.getValue();
            
            if (lockInfo.isHeldBy(failedNodeId)) {
                try {
                    migrateLock(lockName, failedNodeId, nodeId);
                    migratedLocks.add(lockName);
                } catch (Exception e) {
                    logger.error("Failed to migrate lock {}: {}", lockName, e.getMessage());
                    failedLocks.add(lockName);
                }
            }
        }
        
        MigrationResult result = new MigrationResult(
                failedLocks.isEmpty(),
                migratedLocks,
                failedLocks,
                "Migration completed from node " + failedNodeId
        );
        
        notifyMigrationComplete(result);
        
        logger.info("Migration from node {} completed: {} succeeded, {} failed", 
                failedNodeId, migratedLocks.size(), failedLocks.size());
        
        return result;
    }

    private void migrateLock(String lockName, String fromNodeId, String toNodeId) throws Exception {
        LockInfo lockInfo = lockRegistry.get(lockName);
        if (lockInfo == null) {
            throw new Exception("Lock not found: " + lockName);
        }
        
        LockInfo.LockHolder holder = lockInfo.getHolder(fromNodeId);
        if (holder == null) {
            throw new Exception("Node " + fromNodeId + " does not hold lock " + lockName);
        }
        
        LockInfo.LockHolder newHolder = new LockInfo.LockHolder(
                toNodeId,
                holder.getLockToken(),
                holder.getLockType(),
                holder.getLeaseId(),
                holder.getExpireTime()
        );
        
        synchronized (lockInfo) {
            lockInfo.removeHolder(fromNodeId);
            
            String lockKey = etcdClient.getLockKey(lockName);
            try {
                etcdClient.delete(lockKey).get(3, TimeUnit.SECONDS);
            } catch (Exception e) {
                logger.warn("Failed to delete old lock key for {}: {}", lockName, e.getMessage());
            }
            
            logger.info("Lock {} migrated from node {} to node {}", lockName, fromNodeId, toNodeId);
        }
    }

    public MigrationResult migrateLocks(String fromNodeId, String toNodeId, List<String> lockNames) {
        List<String> migratedLocks = new ArrayList<>();
        List<String> failedLocks = new ArrayList<>();
        
        for (String lockName : lockNames) {
            try {
                migrateLock(lockName, fromNodeId, toNodeId);
                migratedLocks.add(lockName);
            } catch (Exception e) {
                logger.error("Failed to migrate lock {}: {}", lockName, e.getMessage());
                failedLocks.add(lockName);
            }
        }
        
        MigrationResult result = new MigrationResult(
                failedLocks.isEmpty(),
                migratedLocks,
                failedLocks,
                "Manual migration completed"
        );
        
        notifyMigrationComplete(result);
        
        return result;
    }

    private void notifyMigrationComplete(MigrationResult result) {
        for (MigrationListener listener : migrationListeners) {
            try {
                listener.onMigrationComplete(result);
            } catch (Exception e) {
                logger.error("Error in migration listener", e);
            }
        }
    }

    public NodeInfo getNodeInfo(String nodeId) {
        return clusterNodes.get(nodeId);
    }

    public Collection<NodeInfo> getAllNodeInfos() {
        return clusterNodes.values();
    }

    public boolean isNodeHealthy(String nodeId) {
        NodeInfo nodeInfo = clusterNodes.get(nodeId);
        return nodeInfo != null && nodeInfo.isHealthy();
    }

    public interface MigrationListener {
        void onMigrationComplete(MigrationResult result);
    }

    public static class NodeInfo {
        private final String nodeId;
        private final long startTimeMs;
        private volatile long lastHeartbeatMs;
        private volatile boolean healthy;

        public NodeInfo(String nodeId, long startTimeMs) {
            this.nodeId = nodeId;
            this.startTimeMs = startTimeMs;
            this.lastHeartbeatMs = System.currentTimeMillis();
            this.healthy = true;
        }

        public String getNodeId() {
            return nodeId;
        }

        public long getStartTimeMs() {
            return startTimeMs;
        }

        public long getLastHeartbeatMs() {
            return lastHeartbeatMs;
        }

        public void setLastHeartbeatMs(long lastHeartbeatMs) {
            this.lastHeartbeatMs = lastHeartbeatMs;
        }

        public boolean isHealthy() {
            return healthy;
        }

        public void setHealthy(boolean healthy) {
            this.healthy = healthy;
        }

        public long getUptimeMs() {
            return System.currentTimeMillis() - startTimeMs;
        }
    }

    public static class MigrationResult {
        private final boolean success;
        private final List<String> migratedLocks;
        private final List<String> failedLocks;
        private final String message;

        public MigrationResult(boolean success, List<String> migratedLocks, 
                               List<String> failedLocks, String message) {
            this.success = success;
            this.migratedLocks = migratedLocks;
            this.failedLocks = failedLocks;
            this.message = message;
        }

        public boolean isSuccess() {
            return success;
        }

        public List<String> getMigratedLocks() {
            return migratedLocks;
        }

        public List<String> getFailedLocks() {
            return failedLocks;
        }

        public String getMessage() {
            return message;
        }
    }
}
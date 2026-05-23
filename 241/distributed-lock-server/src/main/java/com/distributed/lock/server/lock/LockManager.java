package com.distributed.lock.server.lock;

import com.distributed.lock.proto.LockType;
import com.distributed.lock.server.config.LockServerConfig;
import com.distributed.lock.server.deadlock.DeadlockDetector;
import com.distributed.lock.server.etcd.EtcdClient;
import com.distributed.lock.server.metrics.LockContentionAnalyzer;
import com.distributed.lock.server.metrics.LockMetrics;
import com.distributed.lock.server.migration.LockMigrationManager;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

public class LockManager implements AutoCloseable {
    
    private static final Logger logger = LoggerFactory.getLogger(LockManager.class);
    
    private final EtcdClient etcdClient;
    private final LockServerConfig config;
    private final ConcurrentHashMap<String, LockInfo> lockRegistry;
    private final ScheduledExecutorService[] leaseRenewExecutors;
    private final int shardCount;
    private final ScheduledExecutorService cleanupExecutor;
    private final ScheduledExecutorService heartbeatChecker;
    private final ObjectMapper objectMapper;
    private final long heartbeatTimeoutMs;
    private final List<Consumer<HeartbeatLostEvent>> heartbeatLostListeners;
    
    private final LockContentionAnalyzer contentionAnalyzer;
    private final DeadlockDetector deadlockDetector;
    private final LockMigrationManager migrationManager;
    private final ConcurrentHashMap<String, Long> lockAcquireTimes;
    
    private final String nodeId;
    private final long startTimeMs;
    
    private final AtomicLong acquireSuccessCount = new AtomicLong(0);
    private final AtomicLong acquireFailCount = new AtomicLong(0);
    private final AtomicLong releaseCount = new AtomicLong(0);
    private final AtomicLong heartbeatLostCount = new AtomicLong(0);

    public LockManager(EtcdClient etcdClient, LockServerConfig config) {
        this(etcdClient, config, UUID.randomUUID().toString());
    }

    public LockManager(EtcdClient etcdClient, LockServerConfig config, String nodeId) {
        this.etcdClient = etcdClient;
        this.config = config;
        this.nodeId = nodeId;
        this.startTimeMs = System.currentTimeMillis();
        this.lockRegistry = new ConcurrentHashMap<>();
        this.objectMapper = new ObjectMapper();
        this.shardCount = Runtime.getRuntime().availableProcessors();
        this.leaseRenewExecutors = new ScheduledExecutorService[shardCount];
        this.heartbeatTimeoutMs = config.getDefaultLeaseTtlSeconds() * 1000 / 2;
        this.heartbeatLostListeners = new CopyOnWriteArrayList<>();
        this.lockAcquireTimes = new ConcurrentHashMap<>();
        
        this.contentionAnalyzer = new LockContentionAnalyzer();
        this.deadlockDetector = new DeadlockDetector(lockRegistry, 30000, true);
        this.migrationManager = new LockMigrationManager(etcdClient, config, lockRegistry, nodeId);
        
        for (int i = 0; i < shardCount; i++) {
            final int shardIndex = i;
            this.leaseRenewExecutors[i] = Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "lease-renew-shard-" + shardIndex);
                t.setDaemon(true);
                return t;
            });
        }
        
        this.cleanupExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "cleanup-thread");
            t.setDaemon(true);
            return t;
        });
        
        this.heartbeatChecker = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "heartbeat-checker");
            t.setDaemon(true);
            return t;
        });
        
        if (config.isLeaseAutoRenewEnabled()) {
            startLeaseRenewTask();
        }
        startCleanupTask();
        startHeartbeatCheckTask();
        deadlockDetector.start();
        migrationManager.start();
        
        logger.info("LockManager initialized with {} lease renew shards, nodeId: {}", shardCount, nodeId);
    }

    private int getShardIndex(String lockName) {
        return Math.abs(lockName.hashCode() % shardCount);
    }

    private void startLeaseRenewTask() {
        long renewInterval = config.getLeaseRenewIntervalSeconds();
        
        for (int shard = 0; shard < shardCount; shard++) {
            final int currentShard = shard;
            leaseRenewExecutors[shard].scheduleAtFixedRate(() -> {
                for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
                    String lockName = entry.getKey();
                    if (getShardIndex(lockName) != currentShard) {
                        continue;
                    }
                    
                    LockInfo lockInfo = entry.getValue();
                    for (LockInfo.LockHolder holder : lockInfo.getHolders().values()) {
                        if (!holder.isExpired()) {
                            try {
                                etcdClient.keepAliveOnce(holder.getLeaseId());
                                holder.setExpireTime(System.currentTimeMillis() + config.getDefaultLeaseTtlSeconds() * 1000);
                            } catch (Exception e) {
                                logger.warn("Failed to renew lease for lock {} holder {}: {}", 
                                        lockName, holder.getClientId(), e.getMessage());
                            }
                        }
                    }
                }
            }, renewInterval, renewInterval, TimeUnit.SECONDS);
        }
    }

    private void startCleanupTask() {
        cleanupExecutor.scheduleAtFixedRate(() -> {
            for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
                LockInfo lockInfo = entry.getValue();
                Iterator<Map.Entry<String, LockInfo.LockHolder>> iter = lockInfo.getHolders().entrySet().iterator();
                while (iter.hasNext()) {
                    Map.Entry<String, LockInfo.LockHolder> holderEntry = iter.next();
                    if (holderEntry.getValue().isExpired()) {
                        logger.warn("Lock {} held by {} expired, removing", entry.getKey(), holderEntry.getKey());
                        iter.remove();
                    }
                }
                
                Iterator<LockInfo.Waiter> waiterIter = lockInfo.getWaitQueue().iterator();
                while (waiterIter.hasNext()) {
                    LockInfo.Waiter waiter = waiterIter.next();
                    if (waiter.isTimedOut()) {
                        lockInfo.removeWaiter(waiter);
                    }
                }
            }
        }, 10, 10, TimeUnit.SECONDS);
    }

    private void startHeartbeatCheckTask() {
        heartbeatChecker.scheduleAtFixedRate(() -> {
            List<HeartbeatLostEvent> lostEvents = new ArrayList<>();
            
            for (Map.Entry<String, LockInfo> entry : lockRegistry.entrySet()) {
                String lockName = entry.getKey();
                LockInfo lockInfo = entry.getValue();
                
                Iterator<Map.Entry<String, LockInfo.LockHolder>> iter = lockInfo.getHolders().entrySet().iterator();
                while (iter.hasNext()) {
                    Map.Entry<String, LockInfo.LockHolder> holderEntry = iter.next();
                    LockInfo.LockHolder holder = holderEntry.getValue();
                    
                    if (holder.isHeartbeatExpired(heartbeatTimeoutMs)) {
                        logger.error("Heartbeat lost for lock {} holder {}, force releasing lock", 
                                lockName, holder.getClientId());
                        
                        HeartbeatLostEvent event = new HeartbeatLostEvent(
                                lockName, 
                                holder.getClientId(), 
                                holder.getLastHeartbeatTime(),
                                System.currentTimeMillis()
                        );
                        lostEvents.add(event);
                        
                        try {
                            etcdClient.delete(etcdClient.getLockKey(lockName)).get(3, TimeUnit.SECONDS);
                        } catch (Exception e) {
                            logger.warn("Failed to delete etcd key for lock {}: {}", lockName, e.getMessage());
                        }
                        
                        iter.remove();
                        heartbeatLostCount.incrementAndGet();
                    }
                }
            }
            
            for (HeartbeatLostEvent event : lostEvents) {
                notifyHeartbeatLost(event);
            }
        }, heartbeatTimeoutMs / 2, heartbeatTimeoutMs / 2, TimeUnit.MILLISECONDS);
    }

    public void addHeartbeatLostListener(Consumer<HeartbeatLostEvent> listener) {
        heartbeatLostListeners.add(listener);
    }

    private void notifyHeartbeatLost(HeartbeatLostEvent event) {
        for (Consumer<HeartbeatLostEvent> listener : heartbeatLostListeners) {
            try {
                listener.accept(event);
            } catch (Exception e) {
                logger.error("Error in heartbeat lost listener", e);
            }
        }
    }

    public HeartbeatResult processHeartbeat(String clientId, List<String> heldLocks) {
        List<String> expiredLocks = new ArrayList<>();
        
        for (String lockName : heldLocks) {
            LockInfo lockInfo = lockRegistry.get(lockName);
            if (lockInfo != null && lockInfo.isHeldBy(clientId)) {
                lockInfo.updateHeartbeat(clientId);
            } else {
                expiredLocks.add(lockName);
            }
        }
        
        migrationManager.updateNodeHeartbeat(clientId);
        
        return new HeartbeatResult(true, heartbeatTimeoutMs, expiredLocks);
    }

    public LockResult tryLock(String lockName, String clientId, LockType lockType, long ttlSeconds, boolean reentrant) {
        LockInfo lockInfo = getOrCreateLockInfo(lockName);
        
        synchronized (lockInfo) {
            if (canAcquireLock(lockInfo, clientId, lockType, reentrant)) {
                return doAcquireLock(lockInfo, lockName, clientId, lockType, ttlSeconds, reentrant);
            }
            acquireFailCount.incrementAndGet();
            return new LockResult(false, null, 0, "Lock not available");
        }
    }

    public LockResult lock(String lockName, String clientId, LockType lockType, long ttlSeconds, long timeoutMs, boolean reentrant) {
        LockInfo lockInfo = getOrCreateLockInfo(lockName);
        long startTime = System.currentTimeMillis();
        
        contentionAnalyzer.recordLockAttempt(lockName, clientId);
        
        while (System.currentTimeMillis() - startTime < timeoutMs) {
            synchronized (lockInfo) {
                if (canAcquireLock(lockInfo, clientId, lockType, reentrant)) {
                    LockResult result = doAcquireLock(lockInfo, lockName, clientId, lockType, ttlSeconds, reentrant);
                    contentionAnalyzer.recordLockAcquired(lockName, clientId);
                    return result;
                }
                
                try {
                    long remaining = timeoutMs - (System.currentTimeMillis() - startTime);
                    if (remaining > 0) {
                        lockInfo.wait(Math.min(remaining, 100));
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    acquireFailCount.incrementAndGet();
                    return new LockResult(false, null, 0, "Lock interrupted");
                }
            }
        }
        
        acquireFailCount.incrementAndGet();
        return new LockResult(false, null, 0, "Lock timeout");
    }

    private boolean canAcquireLock(LockInfo lockInfo, String clientId, LockType lockType, boolean reentrant) {
        if (!lockInfo.isLocked()) {
            return true;
        }
        
        if (reentrant && lockInfo.isHeldBy(clientId)) {
            LockInfo.LockHolder holder = lockInfo.getHolder(clientId);
            return isLockTypeCompatible(holder.getLockType(), lockType);
        }
        
        if (lockType == LockType.READ) {
            if (lockInfo.hasWaitingWriteLock()) {
                return false;
            }
            return lockInfo.isReadLocked();
        }
        
        return false;
    }

    private boolean isLockTypeCompatible(LockType heldType, LockType requestedType) {
        if (heldType == requestedType) {
            return true;
        }
        if (heldType == LockType.WRITE && requestedType == LockType.READ) {
            return true;
        }
        return false;
    }

    private LockResult doAcquireLock(LockInfo lockInfo, String lockName, String clientId, LockType lockType, 
                                     long ttlSeconds, boolean reentrant) {
        try {
            if (reentrant && lockInfo.isHeldBy(clientId)) {
                LockInfo.LockHolder holder = lockInfo.getHolder(clientId);
                int newCount = holder.incrementHoldCount();
                lockInfo.updateHeartbeat(clientId);
                logger.debug("Reentrant lock {} acquired by {}, count: {}", lockName, clientId, newCount);
                acquireSuccessCount.incrementAndGet();
                return new LockResult(true, holder.getLockToken(), holder.getLeaseId(), "Reentrant lock acquired");
            }
            
            long actualTtl = ttlSeconds > 0 ? ttlSeconds : config.getDefaultLeaseTtlSeconds();
            long leaseId = etcdClient.grantLease(actualTtl).get(5, TimeUnit.SECONDS);
            
            String lockToken = UUID.randomUUID().toString();
            String lockKey = etcdClient.getLockKey(lockName);
            
            LockValue lockValue = new LockValue(clientId, lockType, lockToken, leaseId, actualTtl);
            etcdClient.putWithLease(lockKey, objectMapper.writeValueAsString(lockValue), leaseId)
                    .get(5, TimeUnit.SECONDS);
            
            lockInfo.addHolder(clientId, lockToken, lockType, leaseId, actualTtl);
            lockAcquireTimes.put(lockName + ":" + clientId, System.currentTimeMillis());
            
            logger.debug("Lock {} acquired by {} with type {}", lockName, clientId, lockType);
            acquireSuccessCount.incrementAndGet();
            
            return new LockResult(true, lockToken, leaseId, "Lock acquired");
        } catch (Exception e) {
            logger.error("Failed to acquire lock {}: {}", lockName, e.getMessage(), e);
            acquireFailCount.incrementAndGet();
            return new LockResult(false, null, 0, "Failed to acquire lock: " + e.getMessage());
        }
    }

    public UnlockResult unlock(String lockName, String lockToken, String clientId) {
        LockInfo lockInfo = lockRegistry.get(lockName);
        if (lockInfo == null) {
            return new UnlockResult(false, "Lock not found");
        }
        
        synchronized (lockInfo) {
            LockInfo.LockHolder holder = lockInfo.getHolder(clientId);
            if (holder == null) {
                return new UnlockResult(false, "Not holding the lock");
            }
            
            if (!holder.getLockToken().equals(lockToken)) {
                return new UnlockResult(false, "Invalid lock token");
            }
            
            int remainingCount = holder.decrementHoldCount();
            if (remainingCount > 0) {
                logger.debug("Released reentrant lock {}, remaining count: {}", lockName, remainingCount);
                return new UnlockResult(true, "Reentrant lock released, count: " + remainingCount);
            }
            
            Long acquireTime = lockAcquireTimes.remove(lockName + ":" + clientId);
            if (acquireTime != null) {
                long holdTime = System.currentTimeMillis() - acquireTime;
                contentionAnalyzer.recordLockReleased(lockName, holdTime);
            }
            
            lockInfo.removeHolder(clientId);
            
            try {
                etcdClient.delete(etcdClient.getLockKey(lockName)).get(5, TimeUnit.SECONDS);
            } catch (Exception e) {
                logger.warn("Failed to delete etcd key for lock {}: {}", lockName, e.getMessage());
            }
            
            releaseCount.incrementAndGet();
            logger.debug("Lock {} released by {}", lockName, clientId);
            
            lockInfo.notifyAll();
            
            notifyNextWaiter(lockInfo);
            
            return new UnlockResult(true, "Lock released");
        }
    }

    private void notifyNextWaiter(LockInfo lockInfo) {
        for (LockInfo.Waiter waiter : lockInfo.getWaitQueue()) {
            if (canAcquireLock(lockInfo, waiter.getClientId(), waiter.getLockType(), false)) {
                lockInfo.removeWaiter(waiter);
                waiter.notifyAcquired();
                break;
            }
        }
    }

    public RenewResult renewLease(String lockName, String lockToken, long leaseId) {
        LockInfo lockInfo = lockRegistry.get(lockName);
        if (lockInfo == null) {
            return new RenewResult(false, 0, "Lock not found");
        }
        
        for (LockInfo.LockHolder holder : lockInfo.getHolders().values()) {
            if (holder.getLockToken().equals(lockToken) && holder.getLeaseId() == leaseId) {
                try {
                    etcdClient.keepAliveOnce(leaseId);
                    long newExpireTime = System.currentTimeMillis() + config.getDefaultLeaseTtlSeconds() * 1000;
                    holder.setExpireTime(newExpireTime);
                    return new RenewResult(true, config.getDefaultLeaseTtlSeconds(), "Lease renewed");
                } catch (Exception e) {
                    logger.error("Failed to renew lease for lock {}: {}", lockName, e.getMessage());
                    return new RenewResult(false, 0, "Failed to renew lease: " + e.getMessage());
                }
            }
        }
        
        return new RenewResult(false, 0, "Lock token or lease ID mismatch");
    }

    public List<LockContentionAnalyzer.LockMetrics> getHotLocks(int topN) {
        return contentionAnalyzer.getHotLocks(topN);
    }

    public Collection<LockContentionAnalyzer.LockMetrics> getAllLockMetrics() {
        return contentionAnalyzer.getAllLockMetrics();
    }

    public LockMetrics getLockMetrics(String lockName) {
        return contentionAnalyzer.getLockMetrics(lockName);
    }

    public double getOverallAvgWaitTimeMs() {
        return contentionAnalyzer.getOverallAvgWaitTimeMs();
    }

    public double getOverallAvgHoldTimeMs() {
        return contentionAnalyzer.getOverallAvgHoldTimeMs();
    }

    public List<DeadlockDetector.DeadlockInfo> detectDeadlocks(boolean autoResolve) {
        return deadlockDetector.detectDeadlocks(autoResolve);
    }

    public LockMigrationManager.MigrationResult migrateLocks(String fromNodeId, String toNodeId, List<String> lockNames) {
        return migrationManager.migrateLocks(fromNodeId, toNodeId, lockNames);
    }

    public LockMigrationManager.MigrationResult migrateLocksFromFailedNode(String failedNodeId) {
        return migrationManager.migrateLocksFromFailedNode(failedNodeId);
    }

    public LockMigrationManager.NodeInfo getNodeInfo(String nodeId) {
        return migrationManager.getNodeInfo(nodeId);
    }

    public Collection<LockMigrationManager.NodeInfo> getAllNodeInfos() {
        return migrationManager.getAllNodeInfos();
    }

    public String getNodeId() {
        return nodeId;
    }

    public long getUptimeMs() {
        return System.currentTimeMillis() - startTimeMs;
    }

    public void registerNode(String nodeId) {
        migrationManager.registerNode(nodeId);
    }

    public LockInfo getLockInfo(String lockName) {
        return lockRegistry.get(lockName);
    }

    public Collection<LockInfo> getAllLockInfos() {
        return lockRegistry.values();
    }

    private LockInfo getOrCreateLockInfo(String lockName) {
        return lockRegistry.computeIfAbsent(lockName, LockInfo::new);
    }

    public long getAcquireSuccessCount() {
        return acquireSuccessCount.get();
    }

    public long getAcquireFailCount() {
        return acquireFailCount.get();
    }

    public long getReleaseCount() {
        return releaseCount.get();
    }

    public long getHeartbeatLostCount() {
        return heartbeatLostCount.get();
    }

    public LockContentionAnalyzer getContentionAnalyzer() {
        return contentionAnalyzer;
    }

    public DeadlockDetector getDeadlockDetector() {
        return deadlockDetector;
    }

    public LockMigrationManager getMigrationManager() {
        return migrationManager;
    }

    @Override
    public void close() {
        logger.info("Closing LockManager...");
        
        deadlockDetector.stop();
        migrationManager.stop();
        
        for (ScheduledExecutorService executor : leaseRenewExecutors) {
            executor.shutdown();
        }
        cleanupExecutor.shutdown();
        heartbeatChecker.shutdown();
        
        try {
            for (ScheduledExecutorService executor : leaseRenewExecutors) {
                if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            }
            if (!cleanupExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                cleanupExecutor.shutdownNow();
            }
            if (!heartbeatChecker.awaitTermination(5, TimeUnit.SECONDS)) {
                heartbeatChecker.shutdownNow();
            }
        } catch (InterruptedException e) {
            for (ScheduledExecutorService executor : leaseRenewExecutors) {
                executor.shutdownNow();
            }
            cleanupExecutor.shutdownNow();
            heartbeatChecker.shutdownNow();
            Thread.currentThread().interrupt();
        }
        
        logger.info("LockManager closed");
    }

    public static class HeartbeatLostEvent {
        private final String lockName;
        private final String clientId;
        private final long lastHeartbeatTime;
        private final long detectedTime;

        public HeartbeatLostEvent(String lockName, String clientId, long lastHeartbeatTime, long detectedTime) {
            this.lockName = lockName;
            this.clientId = clientId;
            this.lastHeartbeatTime = lastHeartbeatTime;
            this.detectedTime = detectedTime;
        }

        public String getLockName() {
            return lockName;
        }

        public String getClientId() {
            return clientId;
        }

        public long getLastHeartbeatTime() {
            return lastHeartbeatTime;
        }

        public long getDetectedTime() {
            return detectedTime;
        }
    }

    public static class HeartbeatResult {
        private final boolean success;
        private final long nextHeartbeatMs;
        private final List<String> expiredLocks;

        public HeartbeatResult(boolean success, long nextHeartbeatMs, List<String> expiredLocks) {
            this.success = success;
            this.nextHeartbeatMs = nextHeartbeatMs;
            this.expiredLocks = expiredLocks;
        }

        public boolean isSuccess() {
            return success;
        }

        public long getNextHeartbeatMs() {
            return nextHeartbeatMs;
        }

        public List<String> getExpiredLocks() {
            return expiredLocks;
        }
    }

    public static class LockResult {
        private final boolean success;
        private final String lockToken;
        private final long leaseId;
        private final String message;

        public LockResult(boolean success, String lockToken, long leaseId, String message) {
            this.success = success;
            this.lockToken = lockToken;
            this.leaseId = leaseId;
            this.message = message;
        }

        public boolean isSuccess() {
            return success;
        }

        public String getLockToken() {
            return lockToken;
        }

        public long getLeaseId() {
            return leaseId;
        }

        public String getMessage() {
            return message;
        }
    }

    public static class UnlockResult {
        private final boolean success;
        private final String message;

        public UnlockResult(boolean success, String message) {
            this.success = success;
            this.message = message;
        }

        public boolean isSuccess() {
            return success;
        }

        public String getMessage() {
            return message;
        }
    }

    public static class RenewResult {
        private final boolean success;
        private final long newTtl;
        private final String message;

        public RenewResult(boolean success, long newTtl, String message) {
            this.success = success;
            this.newTtl = newTtl;
            this.message = message;
        }

        public boolean isSuccess() {
            return success;
        }

        public long getNewTtl() {
            return newTtl;
        }

        public String getMessage() {
            return message;
        }
    }

    public static class LockValue {
        private String clientId;
        private LockType lockType;
        private String lockToken;
        private long leaseId;
        private long ttl;

        public LockValue() {}

        public LockValue(String clientId, LockType lockType, String lockToken, long leaseId, long ttl) {
            this.clientId = clientId;
            this.lockType = lockType;
            this.lockToken = lockToken;
            this.leaseId = leaseId;
            this.ttl = ttl;
        }

        public String getClientId() {
            return clientId;
        }

        public void setClientId(String clientId) {
            this.clientId = clientId;
        }

        public LockType getLockType() {
            return lockType;
        }

        public void setLockType(LockType lockType) {
            this.lockType = lockType;
        }

        public String getLockToken() {
            return lockToken;
        }

        public void setLockToken(String lockToken) {
            this.lockToken = lockToken;
        }

        public long getLeaseId() {
            return leaseId;
        }

        public void setLeaseId(long leaseId) {
            this.leaseId = leaseId;
        }

        public long getTtl() {
            return ttl;
        }

        public void setTtl(long ttl) {
            this.ttl = ttl;
        }
    }
}
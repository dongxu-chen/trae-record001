package com.distributed.lock.client;

import com.distributed.lock.client.config.LockClientConfig;
import com.distributed.lock.proto.*;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import io.github.resilience4j.retry.RetryRegistry;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.function.Supplier;

public class DistributedLockClient implements AutoCloseable {
    
    private static final Logger logger = LoggerFactory.getLogger(DistributedLockClient.class);
    
    private final LockClientConfig config;
    private final ManagedChannel channel;
    private final LockServiceGrpc.LockServiceBlockingStub lockStub;
    private final LockMonitorServiceGrpc.LockMonitorServiceBlockingStub monitorStub;
    
    private final CircuitBreaker circuitBreaker;
    private final Retry retry;
    private final ScheduledExecutorService leaseRenewExecutor;
    private final ScheduledExecutorService heartbeatExecutor;
    private final Map<String, LeaseRenewTask> activeLeases;
    private final List<Consumer<HeartbeatLostEvent>> heartbeatLostListeners;
    private volatile long heartbeatIntervalMs;
    private volatile HeartbeatSender heartbeatSender;

    public DistributedLockClient(LockClientConfig config) {
        this.config = config;
        this.channel = ManagedChannelBuilder
                .forAddress(config.getServerHost(), config.getServerPort())
                .usePlaintext()
                .build();
        this.lockStub = LockServiceGrpc.newBlockingStub(channel);
        this.monitorStub = LockMonitorServiceGrpc.newBlockingStub(channel);
        
        this.circuitBreaker = initCircuitBreaker(config);
        this.retry = initRetry(config);
        
        this.leaseRenewExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "client-lease-renew");
            t.setDaemon(true);
            return t;
        });
        this.heartbeatExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "client-heartbeat");
            t.setDaemon(true);
            return t;
        });
        this.activeLeases = new ConcurrentHashMap<>();
        this.heartbeatLostListeners = new ArrayList<>();
        this.heartbeatIntervalMs = config.getDefaultLeaseTtlSeconds() * 1000 / 3;
        
        logger.info("DistributedLockClient initialized with server: {}:{}", 
                config.getServerHost(), config.getServerPort());
    }

    private CircuitBreaker initCircuitBreaker(LockClientConfig config) {
        CircuitBreakerConfig circuitBreakerConfig = CircuitBreakerConfig.custom()
                .failureRateThreshold(config.getCircuitBreakerFailureRateThreshold())
                .waitDurationInOpenState(Duration.ofMillis(config.getCircuitBreakerWaitDurationInOpenStateMs()))
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(config.getCircuitBreakerRingBufferSizeInClosedState())
                .permittedNumberOfCallsInHalfOpenState(config.getCircuitBreakerRingBufferSizeInHalfOpenState())
                .build();
        
        CircuitBreakerRegistry registry = CircuitBreakerRegistry.of(circuitBreakerConfig);
        return registry.circuitBreaker("lockClientCircuitBreaker");
    }

    private Retry initRetry(LockClientConfig config) {
        RetryConfig retryConfig = RetryConfig.custom()
                .maxAttempts(config.getRetryMaxAttempts())
                .waitDuration(Duration.ofMillis(config.getRetryWaitDurationMs()))
                .retryExceptions(StatusRuntimeException.class)
                .build();
        
        RetryRegistry registry = RetryRegistry.of(retryConfig);
        return registry.retry("lockClientRetry");
    }

    public void addHeartbeatLostListener(Consumer<HeartbeatLostEvent> listener) {
        heartbeatLostListeners.add(listener);
    }

    private void startHeartbeatSenderIfNeeded() {
        if (heartbeatSender == null) {
            synchronized (this) {
                if (heartbeatSender == null) {
                    heartbeatSender = new HeartbeatSender();
                    heartbeatSender.start();
                    logger.debug("Heartbeat sender started with interval: {}ms", heartbeatIntervalMs);
                }
            }
        }
    }

    public LockResponse lock(String lockName) {
        return lock(lockName, LockType.EXCLUSIVE, true);
    }

    public LockResponse lock(String lockName, LockType lockType, boolean reentrant) {
        return lock(lockName, lockType, reentrant, config.getDefaultTimeoutMs(), config.getDefaultLeaseTtlSeconds());
    }

    public LockResponse lock(String lockName, LockType lockType, boolean reentrant, 
                             long timeoutMs, long leaseTtlSeconds) {
        LockRequest request = LockRequest.newBuilder()
                .setLockName(lockName)
                .setClientId(config.getClientId())
                .setLockType(lockType)
                .setTimeoutMs(timeoutMs)
                .setLeaseTtlSeconds(leaseTtlSeconds)
                .setReentrant(reentrant)
                .build();
        
        Supplier<LockResponse> supplier = () -> lockStub.lock(request);
        Supplier<LockResponse> decoratedSupplier = CircuitBreaker
                .decorateSupplier(circuitBreaker, Retry.decorateSupplier(retry, supplier));
        
        try {
            LockResponse response = decoratedSupplier.get();
            if (response.getSuccess()) {
                startLeaseRenewal(lockName, response.getLockToken(), response.getLeaseId());
                startHeartbeatSenderIfNeeded();
            }
            return response;
        } catch (Exception e) {
            logger.error("Failed to acquire lock {}: {}", lockName, e.getMessage());
            throw new RuntimeException("Failed to acquire lock", e);
        }
    }

    public TryLockResponse tryLock(String lockName) {
        return tryLock(lockName, LockType.EXCLUSIVE, true);
    }

    public TryLockResponse tryLock(String lockName, LockType lockType, boolean reentrant) {
        return tryLock(lockName, lockType, reentrant, config.getDefaultLeaseTtlSeconds());
    }

    public TryLockResponse tryLock(String lockName, LockType lockType, boolean reentrant, long leaseTtlSeconds) {
        TryLockRequest request = TryLockRequest.newBuilder()
                .setLockName(lockName)
                .setClientId(config.getClientId())
                .setLockType(lockType)
                .setLeaseTtlSeconds(leaseTtlSeconds)
                .setReentrant(reentrant)
                .build();
        
        Supplier<TryLockResponse> supplier = () -> lockStub.tryLock(request);
        Supplier<TryLockResponse> decoratedSupplier = CircuitBreaker
                .decorateSupplier(circuitBreaker, Retry.decorateSupplier(retry, supplier));
        
        try {
            TryLockResponse response = decoratedSupplier.get();
            if (response.getSuccess()) {
                startLeaseRenewal(lockName, response.getLockToken(), response.getLeaseId());
                startHeartbeatSenderIfNeeded();
            }
            return response;
        } catch (Exception e) {
            logger.error("Failed to try lock {}: {}", lockName, e.getMessage());
            throw new RuntimeException("Failed to try lock", e);
        }
    }

    public UnlockResponse unlock(String lockName, String lockToken) {
        UnlockRequest request = UnlockRequest.newBuilder()
                .setLockName(lockName)
                .setLockToken(lockToken)
                .setClientId(config.getClientId())
                .build();
        
        Supplier<UnlockResponse> supplier = () -> lockStub.unlock(request);
        Supplier<UnlockResponse> decoratedSupplier = CircuitBreaker
                .decorateSupplier(circuitBreaker, Retry.decorateSupplier(retry, supplier));
        
        try {
            UnlockResponse response = decoratedSupplier.get();
            stopLeaseRenewal(lockName);
            return response;
        } catch (Exception e) {
            logger.error("Failed to release lock {}: {}", lockName, e.getMessage());
            throw new RuntimeException("Failed to release lock", e);
        }
    }

    public RenewLeaseResponse renewLease(String lockName, String lockToken, long leaseId) {
        RenewLeaseRequest request = RenewLeaseRequest.newBuilder()
                .setLockName(lockName)
                .setLockToken(lockToken)
                .setLeaseId(leaseId)
                .build();
        
        return lockStub.renewLease(request);
    }

    public HeartbeatResponse sendHeartbeat() {
        List<String> heldLocks = new ArrayList<>(activeLeases.keySet());
        
        HeartbeatRequest request = HeartbeatRequest.newBuilder()
                .setClientId(config.getClientId())
                .addAllHeldLocks(heldLocks)
                .setTimestamp(System.currentTimeMillis())
                .build();
        
        try {
            HeartbeatResponse response = lockStub.heartbeat(request);
            if (response.getNextHeartbeatMs() > 0) {
                heartbeatIntervalMs = response.getNextHeartbeatMs();
            }
            
            if (response.getExpiredLocksCount() > 0) {
                for (String expiredLock : response.getExpiredLocksList()) {
                    logger.warn("Lock {} reported as expired by server", expiredLock);
                    stopLeaseRenewal(expiredLock);
                    notifyHeartbeatLost(expiredLock);
                }
            }
            
            return response;
        } catch (Exception e) {
            logger.error("Failed to send heartbeat: {}", e.getMessage());
            throw e;
        }
    }

    private void notifyHeartbeatLost(String lockName) {
        HeartbeatLostEvent event = new HeartbeatLostEvent(lockName, config.getClientId(), System.currentTimeMillis());
        for (Consumer<HeartbeatLostEvent> listener : heartbeatLostListeners) {
            try {
                listener.accept(event);
            } catch (Exception e) {
                logger.error("Error in heartbeat lost listener", e);
            }
        }
    }

    private void startLeaseRenewal(String lockName, String lockToken, long leaseId) {
        long renewInterval = config.getDefaultLeaseTtlSeconds() * 1000 / 3;
        LeaseRenewTask task = new LeaseRenewTask(lockName, lockToken, leaseId, renewInterval);
        LeaseRenewTask existing = activeLeases.put(lockName, task);
        if (existing != null) {
            existing.cancel();
        }
        task.schedule();
    }

    private void stopLeaseRenewal(String lockName) {
        LeaseRenewTask task = activeLeases.remove(lockName);
        if (task != null) {
            task.cancel();
        }
    }

    public LockStatusResponse getLockStatus(String lockName) {
        LockStatusRequest request = LockStatusRequest.newBuilder()
                .setLockName(lockName)
                .build();
        return monitorStub.getLockStatus(request);
    }

    public AllLocksStatusResponse getAllLocksStatus(int pageSize, int pageNumber) {
        AllLocksStatusRequest request = AllLocksStatusRequest.newBuilder()
                .setPageSize(pageSize)
                .setPageNumber(pageNumber)
                .build();
        return monitorStub.getAllLocksStatus(request);
    }

    public LockStatisticsResponse getLockStatistics() {
        LockStatisticsRequest request = LockStatisticsRequest.newBuilder().build();
        return monitorStub.getLockStatistics(request);
    }

    public LockContentionResponse getLockContention(int topN) {
        LockContentionRequest request = LockContentionRequest.newBuilder()
                .setTopN(topN)
                .build();
        return monitorStub.getLockContention(request);
    }

    public LockContentionResponse getLockContention() {
        return getLockContention(10);
    }

    public DeadlockDetectionResponse detectDeadlock(boolean autoResolve) {
        DeadlockDetectionRequest request = DeadlockDetectionRequest.newBuilder()
                .setAutoResolve(autoResolve)
                .build();
        return monitorStub.detectDeadlock(request);
    }

    public DeadlockDetectionResponse detectDeadlock() {
        return detectDeadlock(false);
    }

    public LockMigrationResponse migrateLocks(String fromNodeId, String toNodeId, List<String> lockNames) {
        LockMigrationRequest.Builder builder = LockMigrationRequest.newBuilder()
                .setFromNodeId(fromNodeId)
                .setToNodeId(toNodeId);
        if (lockNames != null && !lockNames.isEmpty()) {
            builder.addAllLockNames(lockNames);
        }
        return monitorStub.migrateLocks(builder.build());
    }

    public LockMigrationResponse migrateLocksFromFailedNode(String failedNodeId) {
        LockMigrationRequest request = LockMigrationRequest.newBuilder()
                .setFromNodeId(failedNodeId)
                .setToNodeId("")
                .build();
        return monitorStub.migrateLocks(request);
    }

    public NodeStatusResponse getNodeStatus() {
        NodeStatusRequest request = NodeStatusRequest.newBuilder().build();
        return monitorStub.getNodeStatus(request);
    }

    @Override
    public void close() {
        logger.info("Closing DistributedLockClient...");
        
        if (heartbeatSender != null) {
            heartbeatSender.stop();
        }
        
        for (LeaseRenewTask task : activeLeases.values()) {
            task.cancel();
        }
        activeLeases.clear();
        
        leaseRenewExecutor.shutdown();
        heartbeatExecutor.shutdown();
        try {
            if (!leaseRenewExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                leaseRenewExecutor.shutdownNow();
            }
            if (!heartbeatExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                heartbeatExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            leaseRenewExecutor.shutdownNow();
            heartbeatExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
        
        channel.shutdown();
        try {
            if (!channel.awaitTermination(5, TimeUnit.SECONDS)) {
                channel.shutdownNow();
            }
        } catch (InterruptedException e) {
            channel.shutdownNow();
            Thread.currentThread().interrupt();
        }
        
        logger.info("DistributedLockClient closed");
    }

    private class LeaseRenewTask implements Runnable {
        private final String lockName;
        private final String lockToken;
        private final long leaseId;
        private final long intervalMs;
        private volatile boolean cancelled = false;

        public LeaseRenewTask(String lockName, String lockToken, long leaseId, long intervalMs) {
            this.lockName = lockName;
            this.lockToken = lockToken;
            this.leaseId = leaseId;
            this.intervalMs = intervalMs;
        }

        public void schedule() {
            leaseRenewExecutor.schedule(this, intervalMs, TimeUnit.MILLISECONDS);
        }

        public void cancel() {
            cancelled = true;
        }

        @Override
        public void run() {
            if (cancelled) {
                return;
            }
            
            try {
                RenewLeaseResponse response = renewLease(lockName, lockToken, leaseId);
                if (response.getSuccess()) {
                    logger.debug("Lease renewed for lock: {}", lockName);
                    schedule();
                } else {
                    logger.warn("Failed to renew lease for lock {}: {}", lockName, response.getMessage());
                    activeLeases.remove(lockName);
                }
            } catch (Exception e) {
                logger.error("Error renewing lease for lock {}: {}", lockName, e.getMessage());
                schedule();
            }
        }
    }

    private class HeartbeatSender implements Runnable {
        private volatile boolean running = false;

        public void start() {
            running = true;
            scheduleNext();
        }

        public void stop() {
            running = false;
        }

        private void scheduleNext() {
            if (running) {
                heartbeatExecutor.schedule(this, heartbeatIntervalMs, TimeUnit.MILLISECONDS);
            }
        }

        @Override
        public void run() {
            if (!running || activeLeases.isEmpty()) {
                scheduleNext();
                return;
            }
            
            try {
                HeartbeatResponse response = sendHeartbeat();
                logger.debug("Heartbeat sent successfully, next in {}ms", response.getNextHeartbeatMs());
            } catch (Exception e) {
                logger.warn("Failed to send heartbeat: {}", e.getMessage());
            }
            
            scheduleNext();
        }
    }

    public static class HeartbeatLostEvent {
        private final String lockName;
        private final String clientId;
        private final long eventTime;

        public HeartbeatLostEvent(String lockName, String clientId, long eventTime) {
            this.lockName = lockName;
            this.clientId = clientId;
            this.eventTime = eventTime;
        }

        public String getLockName() {
            return lockName;
        }

        public String getClientId() {
            return clientId;
        }

        public long getEventTime() {
            return eventTime;
        }
    }
}
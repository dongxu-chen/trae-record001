package com.distributed.lock.server.grpc;

import com.distributed.lock.proto.*;
import com.distributed.lock.server.deadlock.DeadlockDetector;
import com.distributed.lock.server.lock.LockInfo;
import com.distributed.lock.server.lock.LockManager;
import com.distributed.lock.server.metrics.LockMetrics;
import com.distributed.lock.server.migration.LockMigrationManager;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.stream.Collectors;

public class LockMonitorServiceImpl extends LockMonitorServiceGrpc.LockMonitorServiceImplBase {
    
    private static final Logger logger = LoggerFactory.getLogger(LockMonitorServiceImpl.class);
    
    private final LockManager lockManager;

    public LockMonitorServiceImpl(LockManager lockManager) {
        this.lockManager = lockManager;
    }

    @Override
    public void getLockStatus(LockStatusRequest request, StreamObserver<LockStatusResponse> responseObserver) {
        try {
            logger.debug("Received getLockStatus request: lockName={}", request.getLockName());
            
            LockInfo lockInfo = lockManager.getLockInfo(request.getLockName());
            LockStatusResponse response = buildLockStatusResponse(lockInfo, request.getLockName());
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing getLockStatus request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void getAllLocksStatus(AllLocksStatusRequest request, StreamObserver<AllLocksStatusResponse> responseObserver) {
        try {
            logger.debug("Received getAllLocksStatus request");
            
            Collection<LockInfo> allLocks = lockManager.getAllLockInfos();
            int totalCount = allLocks.size();
            
            int pageSize = request.getPageSize() > 0 ? request.getPageSize() : Integer.MAX_VALUE;
            int pageNumber = request.getPageNumber() > 0 ? request.getPageNumber() : 1;
            int startIndex = (pageNumber - 1) * pageSize;
            
            List<LockStatusResponse> lockStatusList = allLocks.stream()
                    .skip(startIndex)
                    .limit(pageSize)
                    .map(lockInfo -> buildLockStatusResponse(lockInfo, lockInfo.getLockName()))
                    .collect(Collectors.toList());
            
            AllLocksStatusResponse response = AllLocksStatusResponse.newBuilder()
                    .addAllLocks(lockStatusList)
                    .setTotalCount(totalCount)
                    .setPageSize(pageSize)
                    .setPageNumber(pageNumber)
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing getAllLocksStatus request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void getLockStatistics(LockStatisticsRequest request, StreamObserver<LockStatisticsResponse> responseObserver) {
        try {
            logger.debug("Received getLockStatistics request");
            
            Collection<LockInfo> allLocks = lockManager.getAllLockInfos();
            long activeLocks = allLocks.stream().filter(LockInfo::isLocked).count();
            long totalWaiting = allLocks.stream().mapToInt(LockInfo::getWaitQueueLength).sum();
            
            LockStatisticsResponse response = LockStatisticsResponse.newBuilder()
                    .setTotalLocks(allLocks.size())
                    .setActiveLocks(activeLocks)
                    .setTotalWaiting(totalWaiting)
                    .setLockAcquireSuccessCount(lockManager.getAcquireSuccessCount())
                    .setLockAcquireFailCount(lockManager.getAcquireFailCount())
                    .setLockReleaseCount(lockManager.getReleaseCount())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing getLockStatistics request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void getLockContention(LockContentionRequest request, StreamObserver<LockContentionResponse> responseObserver) {
        try {
            logger.debug("Received getLockContention request, topN={}", request.getTopN());
            
            int topN = request.getTopN() > 0 ? request.getTopN() : 10;
            
            List<LockContentionInfo> hotLocks = new ArrayList<>();
            for (LockMetrics metrics : lockManager.getHotLocks(topN)) {
                hotLocks.add(buildContentionInfo(metrics));
            }
            
            List<LockContentionInfo> allLocks = new ArrayList<>();
            for (LockMetrics metrics : lockManager.getAllLockMetrics()) {
                allLocks.add(buildContentionInfo(metrics));
            }
            
            LockContentionResponse response = LockContentionResponse.newBuilder()
                    .addAllHotLocks(hotLocks)
                    .addAllAllLocks(allLocks)
                    .setOverallAvgWaitTimeMs(lockManager.getOverallAvgWaitTimeMs())
                    .setOverallAvgHoldTimeMs(lockManager.getOverallAvgHoldTimeMs())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing getLockContention request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void detectDeadlock(DeadlockDetectionRequest request, StreamObserver<DeadlockDetectionResponse> responseObserver) {
        try {
            logger.debug("Received detectDeadlock request, autoResolve={}", request.getAutoResolve());
            
            long startTime = System.currentTimeMillis();
            List<DeadlockDetector.DeadlockInfo> deadlocks = lockManager.detectDeadlocks(request.getAutoResolve());
            long detectionTime = System.currentTimeMillis() - startTime;
            
            DeadlockDetectionResponse.Builder responseBuilder = DeadlockDetectionResponse.newBuilder()
                    .setDeadlockDetected(!deadlocks.isEmpty())
                    .setDetectionTimeMs(detectionTime);
            
            for (DeadlockDetector.DeadlockInfo deadlock : deadlocks) {
                DeadlockInfo protoDeadlock = DeadlockInfo.newBuilder()
                        .addAllInvolvedLocks(deadlock.getInvolvedLocks())
                        .addAllInvolvedClients(deadlock.getInvolvedClients())
                        .setDetectedCycle(deadlock.getDetectedCycle())
                        .setVictimClientId(deadlock.getVictimClientId() != null ? deadlock.getVictimClientId() : "")
                        .setVictimLockName(deadlock.getVictimLockName() != null ? deadlock.getVictimLockName() : "")
                        .setAutoResolved(deadlock.isAutoResolved())
                        .build();
                responseBuilder.addDeadlocks(protoDeadlock);
            }
            
            responseObserver.onNext(responseBuilder.build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing detectDeadlock request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void migrateLocks(LockMigrationRequest request, StreamObserver<LockMigrationResponse> responseObserver) {
        try {
            logger.debug("Received migrateLocks request: from={}, to={}, locks={}", 
                    request.getFromNodeId(), request.getToNodeId(), request.getLockNamesList());
            
            LockMigrationManager.MigrationResult result;
            
            if (request.getLockNamesCount() > 0) {
                result = lockManager.migrateLocks(
                        request.getFromNodeId(),
                        request.getToNodeId(),
                        request.getLockNamesList()
                );
            } else {
                result = lockManager.migrateLocksFromFailedNode(request.getFromNodeId());
            }
            
            LockMigrationResponse response = LockMigrationResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .addAllMigratedLocks(result.getMigratedLocks())
                    .addAllFailedLocks(result.getFailedLocks())
                    .setMessage(result.getMessage())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing migrateLocks request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void getNodeStatus(NodeStatusRequest request, StreamObserver<NodeStatusResponse> responseObserver) {
        try {
            logger.debug("Received getNodeStatus request");
            
            Collection<LockInfo> allLocks = lockManager.getAllLockInfos();
            long activeLocks = allLocks.stream().filter(LockInfo::isLocked).count();
            
            NodeStatusResponse response = NodeStatusResponse.newBuilder()
                    .setNodeId(lockManager.getNodeId())
                    .setIsHealthy(true)
                    .setActiveLocks(activeLocks)
                    .setTotalLocks(allLocks.size())
                    .setUptimeMs(lockManager.getUptimeMs())
                    .setLastHeartbeatMs(System.currentTimeMillis())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing getNodeStatus request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void watchLock(WatchLockRequest request, StreamObserver<WatchLockEvent> responseObserver) {
        logger.info("WatchLock not fully implemented for lock: {}", request.getLockName());
        responseObserver.onCompleted();
    }

    private LockStatusResponse buildLockStatusResponse(LockInfo lockInfo, String lockName) {
        LockStatusResponse.Builder builder = LockStatusResponse.newBuilder()
                .setLockName(lockName)
                .setIsLocked(false)
                .setWaitQueueLength(0);
        
        if (lockInfo != null) {
            builder.setIsLocked(lockInfo.isLocked())
                    .setWaitQueueLength(lockInfo.getWaitQueueLength())
                    .setHolderCount(lockInfo.getHolderCount());
            
            if (lockInfo.isLocked()) {
                builder.setLockType(lockInfo.getCurrentLockType() != null ? lockInfo.getCurrentLockType() : LockType.EXCLUSIVE);
                
                if (!lockInfo.getHolders().isEmpty()) {
                    LockInfo.LockHolder firstHolder = lockInfo.getHolders().values().iterator().next();
                    builder.setHolderClientId(firstHolder.getClientId())
                            .setLeaseExpireTime(firstHolder.getExpireTime());
                }
                
                List<String> waitingClients = new ArrayList<>();
                for (LockInfo.Waiter waiter : lockInfo.getWaitQueue()) {
                    waitingClients.add(waiter.getClientId());
                }
                builder.addAllWaitingClients(waitingClients);
            }
        }
        
        return builder.build();
    }

    private LockContentionInfo buildContentionInfo(LockMetrics metrics) {
        return LockContentionInfo.newBuilder()
                .setLockName(metrics.getLockName())
                .setAcquireCount(metrics.getAcquireCount())
                .setAvgWaitTimeMs(metrics.getAvgWaitTimeMs())
                .setAvgHoldTimeMs(metrics.getAvgHoldTimeMs())
                .setMaxWaitTimeMs(metrics.getMaxWaitTimeMs())
                .setMaxHoldTimeMs(metrics.getMaxHoldTimeMs())
                .setTotalWaiters(metrics.getTotalWaiters())
                .setContentionScore(metrics.getContentionScore())
                .build();
    }
}
package com.distributed.lock.server.grpc;

import com.distributed.lock.proto.*;
import com.distributed.lock.server.lock.LockManager;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class LockServiceImpl extends LockServiceGrpc.LockServiceImplBase {
    
    private static final Logger logger = LoggerFactory.getLogger(LockServiceImpl.class);
    
    private final LockManager lockManager;

    public LockServiceImpl(LockManager lockManager) {
        this.lockManager = lockManager;
    }

    @Override
    public void lock(LockRequest request, StreamObserver<LockResponse> responseObserver) {
        try {
            logger.debug("Received lock request: lockName={}, clientId={}, type={}", 
                    request.getLockName(), request.getClientId(), request.getLockType());
            
            LockManager.LockResult result = lockManager.lock(
                    request.getLockName(),
                    request.getClientId(),
                    request.getLockType(),
                    request.getLeaseTtlSeconds(),
                    request.getTimeoutMs(),
                    request.getReentrant()
            );
            
            LockResponse response = LockResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .setLockToken(result.getLockToken() != null ? result.getLockToken() : "")
                    .setMessage(result.getMessage())
                    .setLeaseId(result.getLeaseId())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing lock request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void unlock(UnlockRequest request, StreamObserver<UnlockResponse> responseObserver) {
        try {
            logger.debug("Received unlock request: lockName={}, clientId={}", 
                    request.getLockName(), request.getClientId());
            
            LockManager.UnlockResult result = lockManager.unlock(
                    request.getLockName(),
                    request.getLockToken(),
                    request.getClientId()
            );
            
            UnlockResponse response = UnlockResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .setMessage(result.getMessage())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing unlock request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void tryLock(TryLockRequest request, StreamObserver<TryLockResponse> responseObserver) {
        try {
            logger.debug("Received tryLock request: lockName={}, clientId={}, type={}", 
                    request.getLockName(), request.getClientId(), request.getLockType());
            
            LockManager.LockResult result = lockManager.tryLock(
                    request.getLockName(),
                    request.getClientId(),
                    request.getLockType(),
                    request.getLeaseTtlSeconds(),
                    request.getReentrant()
            );
            
            TryLockResponse response = TryLockResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .setLockToken(result.getLockToken() != null ? result.getLockToken() : "")
                    .setMessage(result.getMessage())
                    .setLeaseId(result.getLeaseId())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing tryLock request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void renewLease(RenewLeaseRequest request, StreamObserver<RenewLeaseResponse> responseObserver) {
        try {
            logger.debug("Received renewLease request: lockName={}, leaseId={}", 
                    request.getLockName(), request.getLeaseId());
            
            LockManager.RenewResult result = lockManager.renewLease(
                    request.getLockName(),
                    request.getLockToken(),
                    request.getLeaseId()
            );
            
            RenewLeaseResponse response = RenewLeaseResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .setNewTtl(result.getNewTtl())
                    .setMessage(result.getMessage())
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing renewLease request", e);
            responseObserver.onError(e);
        }
    }

    @Override
    public void heartbeat(HeartbeatRequest request, StreamObserver<HeartbeatResponse> responseObserver) {
        try {
            logger.debug("Received heartbeat from client: {}, heldLocks count: {}", 
                    request.getClientId(), request.getHeldLocksCount());
            
            LockManager.HeartbeatResult result = lockManager.processHeartbeat(
                    request.getClientId(),
                    request.getHeldLocksList()
            );
            
            HeartbeatResponse.Builder responseBuilder = HeartbeatResponse.newBuilder()
                    .setSuccess(result.isSuccess())
                    .setNextHeartbeatMs(result.getNextHeartbeatMs());
            
            if (result.getExpiredLocks() != null && !result.getExpiredLocks().isEmpty()) {
                responseBuilder.addAllExpiredLocks(result.getExpiredLocks());
            }
            
            HeartbeatResponse response = responseBuilder
                    .setMessage("Heartbeat processed")
                    .build();
            
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Error processing heartbeat", e);
            responseObserver.onError(e);
        }
    }
}
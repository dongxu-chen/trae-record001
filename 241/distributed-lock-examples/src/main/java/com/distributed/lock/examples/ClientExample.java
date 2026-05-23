package com.distributed.lock.examples;

import com.distributed.lock.client.DistributedLock;
import com.distributed.lock.client.DistributedLockClient;
import com.distributed.lock.client.config.LockClientConfig;
import com.distributed.lock.proto.HeartbeatResponse;
import com.distributed.lock.proto.LockStatisticsResponse;
import com.distributed.lock.proto.LockStatusResponse;
import com.distributed.lock.proto.LockType;

public class ClientExample {
    public static void main(String[] args) {
        LockClientConfig config = LockClientConfig.builder()
                .serverHost("localhost")
                .serverPort(50051)
                .clientId("client-001")
                .defaultTimeoutMs(30000)
                .defaultLeaseTtlSeconds(30)
                .autoRenewLease(true)
                .retryMaxAttempts(3)
                .retryWaitDurationMs(500)
                .circuitBreakerFailureRateThreshold(50.0)
                .build();
        
        try (DistributedLockClient client = new DistributedLockClient(config)) {
            System.out.println("=== Example 1: Heartbeat Listener ===");
            heartbeatListenerExample(client);
            
            System.out.println("\n=== Example 2: Manual Heartbeat ===");
            manualHeartbeatExample(client);
            
            System.out.println("\n=== Example 3: Basic Exclusive Lock ===");
            basicLockExample(client);
            
            System.out.println("\n=== Example 4: Read Write Lock with Writer Priority ===");
            readWriteLockWithWriterPriorityExample(client);
            
            System.out.println("\n=== Example 5: Monitor Lock Status ===");
            monitorStatusExample(client);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    private static void heartbeatListenerExample(DistributedLockClient client) {
        client.addHeartbeatLostListener(event -> {
            System.out.println("⚠️  ALERT: Heartbeat lost!");
            System.out.println("   Lock: " + event.getLockName());
            System.out.println("   Client: " + event.getClientId());
            System.out.println("   Time: " + event.getEventTime());
        });
        System.out.println("Heartbeat lost listener registered");
    }
    
    private static void manualHeartbeatExample(DistributedLockClient client) {
        DistributedLock lock = new DistributedLock(client, "heartbeat-demo");
        lock.lock();
        
        try {
            System.out.println("Lock acquired, sending manual heartbeat...");
            HeartbeatResponse response = client.sendHeartbeat();
            System.out.println("Heartbeat response:");
            System.out.println("  Success: " + response.getSuccess());
            System.out.println("  Next heartbeat: " + response.getNextHeartbeatMs() + "ms");
            System.out.println("  Message: " + response.getMessage());
        } finally {
            lock.unlock();
        }
    }
    
    private static void basicLockExample(DistributedLockClient client) {
        DistributedLock lock = new DistributedLock(client, "resource-001");
        
        System.out.println("Acquiring lock...");
        lock.lock();
        System.out.println("Lock acquired!");
        
        try {
            System.out.println("Performing critical operation...");
            Thread.sleep(1000);
            System.out.println("Critical operation completed");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            lock.unlock();
            System.out.println("Lock released");
        }
    }
    
    private static void readWriteLockWithWriterPriorityExample(DistributedLockClient client) throws InterruptedException {
        System.out.println("Demonstrating write lock priority...");
        System.out.println("When a write lock is waiting, new read locks will be blocked");
        
        LockClientConfig readerConfig = LockClientConfig.builder()
                .serverHost("localhost")
                .serverPort(50051)
                .clientId("reader-001")
                .build();
        
        LockClientConfig writerConfig = LockClientConfig.builder()
                .serverHost("localhost")
                .serverPort(50051)
                .clientId("writer-001")
                .build();
        
        try (DistributedLockClient readerClient = new DistributedLockClient(readerConfig);
             DistributedLockClient writerClient = new DistributedLockClient(writerConfig)) {
            
            DistributedLock readLock1 = new DistributedLock(readerClient, "rw-resource", LockType.READ, true);
            DistributedLock readLock2 = new DistributedLock(readerClient, "rw-resource", LockType.READ, true);
            DistributedLock writeLock = new DistributedLock(writerClient, "rw-resource", LockType.WRITE, true);
            
            System.out.println("Reader 1 acquiring read lock...");
            readLock1.lock();
            System.out.println("Reader 1: read lock acquired");
            
            System.out.println("Writer requesting write lock (will wait)...");
            Thread writerThread = new Thread(() -> {
                System.out.println("Writer: waiting for write lock...");
                writeLock.lock();
                System.out.println("Writer: write lock acquired!");
                try {
                    Thread.sleep(500);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    writeLock.unlock();
                    System.out.println("Writer: write lock released");
                }
            });
            writerThread.start();
            
            Thread.sleep(100);
            
            System.out.println("Reader 2 trying to acquire read lock (should be blocked due to waiting writer)...");
            long startTime = System.currentTimeMillis();
            boolean gotLock = readLock2.tryLock();
            long waitTime = System.currentTimeMillis() - startTime;
            
            if (gotLock) {
                System.out.println("Reader 2: got lock unexpectedly! Wait time: " + waitTime + "ms");
                readLock2.unlock();
            } else {
                System.out.println("Reader 2: lock blocked (as expected) due to waiting writer!");
                System.out.println("  This demonstrates write lock priority - preventing write starvation");
            }
            
            readLock1.unlock();
            System.out.println("Reader 1: read lock released");
            
            writerThread.join(2000);
        }
    }
    
    private static void monitorStatusExample(DistributedLockClient client) {
        LockStatusResponse status = client.getLockStatus("resource-001");
        System.out.println("Lock Status:");
        System.out.println("  Name: " + status.getLockName());
        System.out.println("  Locked: " + status.getIsLocked());
        System.out.println("  Holder: " + status.getHolderClientId());
        System.out.println("  Wait Queue Length: " + status.getWaitQueueLength());
        System.out.println("  Waiting Write Locks: " + (status.getWaitQueueLength() > 0 ? "check details" : "none"));
        
        LockStatisticsResponse stats = client.getLockStatistics();
        System.out.println("\nLock Statistics:");
        System.out.println("  Total Locks: " + stats.getTotalLocks());
        System.out.println("  Active Locks: " + stats.getActiveLocks());
        System.out.println("  Total Waiting: " + stats.getTotalWaiting());
        System.out.println("  Acquire Success: " + stats.getLockAcquireSuccessCount());
        System.out.println("  Acquire Fail: " + stats.getLockAcquireFailCount());
    }
}
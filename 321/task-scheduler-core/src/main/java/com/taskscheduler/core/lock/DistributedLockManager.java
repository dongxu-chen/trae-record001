package com.taskscheduler.core.lock;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.CuratorFrameworkFactory;
import org.apache.curator.framework.recipes.locks.InterProcessMutex;
import org.apache.curator.retry.ExponentialBackoffRetry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class DistributedLockManager {

    private static final String ZK_ROOT_PATH = "/task-scheduler";
    private static final String ZK_LOCK_PATH = ZK_ROOT_PATH + "/locks";

    @Value("${task-scheduler.zookeeper.address:127.0.0.1:2181}")
    private String zkAddress;

    private CuratorFramework client;

    private final Map<String, InterProcessMutex> lockMap = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() throws Exception {
        client = CuratorFrameworkFactory.newClient(zkAddress,
                new ExponentialBackoffRetry(1000, 3));
        client.start();

        if (client.checkExists().forPath(ZK_LOCK_PATH) == null) {
            client.create().creatingParentsIfNeeded().forPath(ZK_LOCK_PATH);
        }

        log.info("DistributedLockManager initialized with zk: {}", zkAddress);
    }

    @PreDestroy
    public void destroy() throws Exception {
        for (Map.Entry<String, InterProcessMutex> entry : lockMap.entrySet()) {
            try {
                InterProcessMutex lock = entry.getValue();
                if (lock.isAcquiredInThisProcess()) {
                    lock.release();
                }
            } catch (Exception e) {
                log.warn("Release lock failed: {}", entry.getKey(), e);
            }
        }
        lockMap.clear();

        if (client != null) {
            client.close();
        }
        log.info("DistributedLockManager destroyed");
    }

    private String getLockPath(String lockKey) {
        return ZK_LOCK_PATH + "/" + lockKey;
    }

    private String getShardLockKey(Long taskId, Long logId, Integer shardIndex) {
        return "task_" + taskId + "_log_" + logId + "_shard_" + shardIndex;
    }

    public boolean tryLockShard(Long taskId, Long logId, Integer shardIndex, long timeout, TimeUnit unit) {
        String lockKey = getShardLockKey(taskId, logId, shardIndex);
        String lockPath = getLockPath(lockKey);

        try {
            if (client.checkExists().forPath(lockPath) == null) {
                client.create().creatingParentsIfNeeded().forPath(lockPath);
            }

            InterProcessMutex lock = new InterProcessMutex(client, lockPath);
            boolean acquired = lock.acquire(timeout, unit);

            if (acquired) {
                lockMap.put(lockKey, lock);
                log.info("Shard lock acquired: taskId={}, logId={}, shardIndex={}", taskId, logId, shardIndex);
                return true;
            } else {
                log.info("Shard lock acquisition timeout: taskId={}, logId={}, shardIndex={}", taskId, logId, shardIndex);
                return false;
            }
        } catch (Exception e) {
            log.error("Try lock shard failed, taskId={}, logId={}, shardIndex={}", taskId, logId, shardIndex, e);
            return false;
        }
    }

    public boolean tryLockShard(Long taskId, Long logId, Integer shardIndex) {
        return tryLockShard(taskId, logId, shardIndex, 5, TimeUnit.SECONDS);
    }

    public void releaseShardLock(Long taskId, Long logId, Integer shardIndex) {
        String lockKey = getShardLockKey(taskId, logId, shardIndex);
        InterProcessMutex lock = lockMap.remove(lockKey);

        if (lock != null && lock.isAcquiredInThisProcess()) {
            try {
                lock.release();
                log.info("Shard lock released: taskId={}, logId={}, shardIndex={}", taskId, logId, shardIndex);
            } catch (Exception e) {
                log.error("Release shard lock failed, taskId={}, logId={}, shardIndex={}", taskId, logId, shardIndex, e);
            }
        }
    }

    public boolean isShardLocked(Long taskId, Long logId, Integer shardIndex) {
        String lockKey = getShardLockKey(taskId, logId, shardIndex);
        InterProcessMutex lock = lockMap.get(lockKey);
        return lock != null && lock.isAcquiredInThisProcess();
    }

    public boolean tryLock(String lockKey, long timeout, TimeUnit unit) {
        String lockPath = getLockPath(lockKey);

        try {
            if (client.checkExists().forPath(lockPath) == null) {
                client.create().creatingParentsIfNeeded().forPath(lockPath);
            }

            InterProcessMutex lock = new InterProcessMutex(client, lockPath);
            boolean acquired = lock.acquire(timeout, unit);

            if (acquired) {
                lockMap.put(lockKey, lock);
                log.info("Lock acquired: {}", lockKey);
                return true;
            }
            return false;
        } catch (Exception e) {
            log.error("Try lock failed: {}", lockKey, e);
            return false;
        }
    }

    public void releaseLock(String lockKey) {
        InterProcessMutex lock = lockMap.remove(lockKey);
        if (lock != null && lock.isAcquiredInThisProcess()) {
            try {
                lock.release();
                log.info("Lock released: {}", lockKey);
            } catch (Exception e) {
                log.error("Release lock failed: {}", lockKey, e);
            }
        }
    }
}

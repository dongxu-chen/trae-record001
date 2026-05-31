package com.distributed.lock.controller;

import com.distributed.lock.analysis.AnalysisEventListener;
import com.distributed.lock.analysis.LockTimeoutAdvisor;
import com.distributed.lock.analysis.LockWaitPredictor;
import com.distributed.lock.monitor.MonitorLockEventListener;
import com.distributed.lock.redis.RedisDistributedLock;
import com.distributed.lock.redis.RedisLockFactory;
import com.distributed.lock.zookeeper.ZkDistributedLock;
import com.distributed.lock.zookeeper.ZkLockFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/lock-demo")
public class LockDemoController {

    private final RedisLockFactory redisLockFactory;
    private final ZkLockFactory zkLockFactory;
    private final MonitorLockEventListener monitorListener;
    private final AnalysisEventListener analysisListener;
    private final LockTimeoutAdvisor timeoutAdvisor;
    private final LockWaitPredictor waitPredictor;

    @Autowired
    public LockDemoController(RedisLockFactory redisLockFactory,
                              ZkLockFactory zkLockFactory,
                              MonitorLockEventListener monitorListener,
                              AnalysisEventListener analysisListener,
                              LockTimeoutAdvisor timeoutAdvisor,
                              LockWaitPredictor waitPredictor) {
        this.redisLockFactory = redisLockFactory;
        this.zkLockFactory = zkLockFactory;
        this.monitorListener = monitorListener;
        this.analysisListener = analysisListener;
        this.timeoutAdvisor = timeoutAdvisor;
        this.waitPredictor = waitPredictor;
    }

    @GetMapping("/redis/{lockKey}")
    public Map<String, Object> testRedisLock(@PathVariable String lockKey,
                                             @RequestParam(defaultValue = "3") long waitTime,
                                             @RequestParam(defaultValue = "10") long leaseTime) {
        Map<String, Object> result = new HashMap<>();
        RedisDistributedLock lock = redisLockFactory.getLock(lockKey);

        lock.addEventListener(monitorListener);
        lock.addEventListener(analysisListener);

        try {
            boolean acquired = lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS);
            result.put("lockKey", lockKey);
            result.put("lockType", "REDIS");
            result.put("acquired", acquired);

            if (acquired) {
                Thread.sleep(100);
                lock.unlock();
                result.put("released", true);
            }
        } catch (InterruptedException e) {
            result.put("error", e.getMessage());
            Thread.currentThread().interrupt();
        }

        return result;
    }

    @GetMapping("/zookeeper/{lockKey}")
    public Map<String, Object> testZkLock(@PathVariable String lockKey,
                                          @RequestParam(defaultValue = "3") long waitTime,
                                          @RequestParam(defaultValue = "10") long leaseTime) {
        Map<String, Object> result = new HashMap<>();
        ZkDistributedLock lock = zkLockFactory.getLock(lockKey);

        lock.addEventListener(monitorListener);
        lock.addEventListener(analysisListener);

        try {
            boolean acquired = lock.tryLock(waitTime, leaseTime, TimeUnit.SECONDS);
            result.put("lockKey", lockKey);
            result.put("lockType", "ZOOKEEPER");
            result.put("acquired", acquired);

            if (acquired) {
                Thread.sleep(100);
                lock.unlock();
                result.put("released", true);
            }
        } catch (InterruptedException e) {
            result.put("error", e.getMessage());
            Thread.currentThread().interrupt();
        }

        return result;
    }

    @GetMapping("/concurrent/{lockKey}")
    public Map<String, Object> testConcurrentLock(@PathVariable String lockKey,
                                                  @RequestParam(defaultValue = "10") int threads) {
        Map<String, Object> result = new HashMap<>();
        int[] successCount = {0};
        int[] failCount = {0};

        Thread[] threadArray = new Thread[threads];
        for (int i = 0; i < threads; i++) {
            threadArray[i] = new Thread(() -> {
                RedisDistributedLock lock = redisLockFactory.getLock(lockKey);
                lock.addEventListener(monitorListener);
                lock.addEventListener(analysisListener);

                try {
                    boolean acquired = lock.tryLock(5, 30, TimeUnit.SECONDS);
                    if (acquired) {
                        synchronized (successCount) {
                            successCount[0]++;
                        }
                        Thread.sleep(50);
                        lock.unlock();
                    } else {
                        synchronized (failCount) {
                            failCount[0]++;
                        }
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
            threadArray[i].start();
        }

        for (Thread thread : threadArray) {
            try {
                thread.join();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        result.put("lockKey", lockKey);
        result.put("totalThreads", threads);
        result.put("successCount", successCount[0]);
        result.put("failCount", failCount[0]);

        return result;
    }

    @GetMapping("/smart-redis/{lockKey}")
    public Map<String, Object> testSmartRedisLock(@PathVariable String lockKey) {
        Map<String, Object> result = new HashMap<>();

        LockTimeoutAdvisor.TimeoutConfig timeoutConfig = timeoutAdvisor.getCurrentTimeout(lockKey);
        LockWaitPredictor.WaitPrediction prediction = waitPredictor.predictWaitTime(lockKey);

        long waitTimeMs = timeoutConfig.getWaitTimeoutMs();
        long leaseTimeMs = timeoutConfig.getLeaseTimeoutMs();

        result.put("lockKey", lockKey);
        result.put("autoWaitTimeoutMs", waitTimeMs);
        result.put("autoLeaseTimeoutMs", leaseTimeMs);
        result.put("predictedWaitMs", prediction.isPredicted() ? prediction.getEstimatedWaitTimeMs() : "N/A");
        result.put("confidence", prediction.getConfidence());

        RedisDistributedLock lock = redisLockFactory.getLock(lockKey);
        lock.addEventListener(monitorListener);
        lock.addEventListener(analysisListener);

        try {
            long waitSec = Math.max(1, waitTimeMs / 1000);
            long leaseSec = Math.max(1, leaseTimeMs / 1000);
            boolean acquired = lock.tryLock(waitSec, leaseSec, TimeUnit.SECONDS);

            result.put("acquired", acquired);
            result.put("usedWaitTimeSec", waitSec);
            result.put("usedLeaseTimeSec", leaseSec);

            if (acquired) {
                Thread.sleep(100);
                lock.unlock();
                result.put("released", true);
            }
        } catch (InterruptedException e) {
            result.put("error", e.getMessage());
            Thread.currentThread().interrupt();
        }

        return result;
    }
}
package com.distid.snowflake;

import com.distid.metrics.IdMetrics;
import lombok.extern.slf4j.Slf4j;
import org.apache.curator.framework.CuratorFramework;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

@Slf4j
public class SnowflakeIdService {

    private final CuratorFramework curator;
    private final long datacenterId;
    private final long maxTolerateBackwardMs;
    private final long maxWaitBackwardMs;
    private final IdMetrics metrics;
    private final String podName;
    private final NtpTimeSynchronizer ntpTimeSynchronizer;

    private ConsistentHashWorkerIdAssigner workerIdAssigner;
    private SnowflakeIdWorker idWorker;

    public SnowflakeIdService(CuratorFramework curator, long datacenterId,
                              long maxTolerateBackwardMs, long maxWaitBackwardMs,
                              IdMetrics metrics, String podName,
                              NtpTimeSynchronizer ntpTimeSynchronizer) {
        this.curator = curator;
        this.datacenterId = datacenterId;
        this.maxTolerateBackwardMs = maxTolerateBackwardMs;
        this.maxWaitBackwardMs = maxWaitBackwardMs;
        this.metrics = metrics;
        this.podName = podName;
        this.ntpTimeSynchronizer = ntpTimeSynchronizer;
    }

    @PostConstruct
    public void init() throws Exception {
        workerIdAssigner = new ConsistentHashWorkerIdAssigner(curator, podName);
        workerIdAssigner.init();
        long workerId = workerIdAssigner.getAssignedWorkerId();
        idWorker = new SnowflakeIdWorker(workerId, datacenterId, maxTolerateBackwardMs,
                maxWaitBackwardMs, ntpTimeSynchronizer);
        log.info("SnowflakeIdService initialized with workerId={}, datacenterId={}, podName={}, NTP={}",
                workerId, datacenterId, workerIdAssigner.getPodName(),
                ntpTimeSynchronizer != null ? "enabled" : "disabled");
    }

    public long generateId() {
        long start = System.nanoTime();
        try {
            long id = idWorker.nextId();
            metrics.recordSnowflakeSuccess(System.nanoTime() - start);
            return id;
        } catch (ClockBackwardException e) {
            metrics.recordSnowflakeClockBackward();
            metrics.recordSnowflakeError();
            throw e;
        } catch (Exception e) {
            metrics.recordSnowflakeError();
            throw e;
        }
    }

    public long getWorkerId() {
        return idWorker != null ? idWorker.getWorkerId() : -1;
    }

    public String getPodName() {
        return workerIdAssigner != null ? workerIdAssigner.getPodName() : null;
    }

    public boolean isNtpSynchronized() {
        return ntpTimeSynchronizer != null && ntpTimeSynchronizer.isSynchronizedOk();
    }

    public long getNtpOffsetMs() {
        return ntpTimeSynchronizer != null ? ntpTimeSynchronizer.getNetworkOffsetMs() : 0;
    }

    @PreDestroy
    public void destroy() {
        if (workerIdAssigner != null) {
            workerIdAssigner.release();
        }
        if (ntpTimeSynchronizer != null) {
            ntpTimeSynchronizer.stop();
        }
    }
}

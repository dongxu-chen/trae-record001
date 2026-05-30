package com.distid.ha;

import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;

@Slf4g
public class FailoverManager {

    private final DatacenterRegistry dcRegistry;
    private final CrossDcSyncService crossDcSyncService;
    private final StringRedisTemplate redis;

    private volatile boolean failoverInProgress = false;
    private volatile long lastFailoverCheck = 0;

    public FailoverManager(DatacenterRegistry dcRegistry, CrossDcSyncService crossDcSyncService,
                            StringRedisTemplate redis) {
        this.dcRegistry = dcRegistry;
        this.crossDcSyncService = crossDcSyncService;
        this.redis = redis;
    }

    public boolean checkAndPerformFailover() {
        if (failoverInProgress) return false;
        if (!dcRegistry.isLocalActive()) return false;

        for (DatacenterNode remote : dcRegistry.getRemoteDatacenters()) {
            if (remote.isActive()) {
                boolean alive = crossDcSyncService.isRemoteDcAlive(remote.getDcCode());
                if (!alive) {
                    log.warn("Remote DC {} appears DOWN, initiating failover check", remote.getDcCode());
                    return handleRemoteDcDown(remote);
                }
            }
        }
        return false;
    }

    private boolean handleRemoteDcDown(DatacenterNode downDc) {
        failoverInProgress = true;
        try {
            String lockKey = "distid:failover:lock:" + downDc.getDcCode();
            Boolean locked = redis.opsForValue().setIfAbsent(lockKey,
                    dcRegistry.getLocalDcCode(), 60, java.util.concurrent.TimeUnit.SECONDS);

            if (locked == null || !locked) {
                log.info("Failover already in progress for DC {}", downDc.getDcCode());
                return false;
            }

            log.info("Acquired failover lock for DC {}, this DC {} taking over",
                    downDc.getDcCode(), dcRegistry.getLocalDcCode());

            return true;
        } catch (Exception e) {
            log.error("Failover handling failed for DC {}", downDc.getDcCode(), e);
            return false;
        } finally {
            failoverInProgress = false;
        }
    }

    public DatacenterNode findFailoverTarget() {
        return dcRegistry.findFailoverTarget().orElse(null);
    }

    public String getFailoverStatus() {
        StringBuilder sb = new StringBuilder();
        sb.append("localDc=").append(dcRegistry.getLocalDcCode());
        sb.append(", localStatus=").append(dcRegistry.getLocalStatus());
        sb.append(", remoteDCs=").append(dcRegistry.getRemoteDatacenters().size());
        sb.append(", failoverInProgress=").append(failoverInProgress);

        for (DatacenterNode remote : dcRegistry.getRemoteDatacenters()) {
            boolean alive = crossDcSyncService.isRemoteDcAlive(remote.getDcCode());
            sb.append(", ").append(remote.getDcCode()).append("=").append(alive ? "UP" : "DOWN");
        }
        return sb.toString();
    }
}

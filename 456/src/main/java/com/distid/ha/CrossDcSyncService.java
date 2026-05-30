package com.distid.ha;

import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.util.concurrent.TimeUnit;

@Slf4g
public class CrossDcSyncService {

    private static final String SYNC_PREFIX = "distid:dc-sync:";
    private static final String SEGMENT_ALLOC_PREFIX = "distid:segment-alloc:";

    private final StringRedisTemplate redis;
    private final DatacenterRegistry dcRegistry;

    public CrossDcSyncService(StringRedisTemplate redis, DatacenterRegistry dcRegistry) {
        this.redis = redis;
        this.dcRegistry = dcRegistry;
    }

    public long allocateSegmentRange(String bizTag) {
        String allocKey = SEGMENT_ALLOC_PREFIX + bizTag;
        long dcOffset = dcRegistry.getSegmentOffset();
        long dcStep = dcRegistry.getSegmentStep();

        try {
            String existing = redis.opsForValue().get(allocKey);
            long currentMax;
            if (existing != null) {
                currentMax = Long.parseLong(existing);
            } else {
                currentMax = 0;
            }

            long newMax = currentMax + dcStep;
            long localMax = dcOffset + newMax;

            redis.opsForValue().set(allocKey, String.valueOf(newMax), 24, TimeUnit.HOURS);

            log.info("Allocated segment for bizTag={}: globalMax={}, localMax={}, dcOffset={}",
                    bizTag, newMax, localMax, dcOffset);
            return localMax;
        } catch (Exception e) {
            log.error("Failed to allocate segment for bizTag={}", bizTag, e);
            return dcOffset + System.currentTimeMillis();
        }
    }

    public void syncSegmentAllocation(String bizTag, long maxId) {
        String syncKey = SYNC_PREFIX + dcRegistry.getLocalDcCode() + ":" + bizTag;
        try {
            redis.opsForValue().set(syncKey, String.valueOf(maxId), 1, TimeUnit.HOURS);
        } catch (Exception e) {
            log.warn("Failed to sync segment allocation for bizTag={}", bizTag, e);
        }
    }

    public long getRemoteDcSegmentMax(String dcCode, String bizTag) {
        String syncKey = SYNC_PREFIX + dcCode + ":" + bizTag;
        try {
            String value = redis.opsForValue().get(syncKey);
            return value != null ? Long.parseLong(value) : 0;
        } catch (Exception e) {
            log.warn("Failed to get remote DC segment max for dcCode={}, bizTag={}", dcCode, bizTag, e);
            return 0;
        }
    }

    public void reportLocalHeartbeat() {
        String key = SYNC_PREFIX + "heartbeat:" + dcRegistry.getLocalDcCode();
        try {
            redis.opsForValue().set(key, String.valueOf(System.currentTimeMillis()), 30, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("Failed to report DC heartbeat", e);
        }
    }

    public boolean isRemoteDcAlive(String dcCode) {
        String key = SYNC_PREFIX + "heartbeat:" + dcCode;
        try {
            String value = redis.opsForValue().get(key);
            if (value == null) return false;
            long lastHeartbeat = Long.parseLong(value);
            return (System.currentTimeMillis() - lastHeartbeat) < 30000;
        } catch (Exception e) {
            return false;
        }
    }
}

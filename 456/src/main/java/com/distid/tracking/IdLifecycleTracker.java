package com.distid.tracking;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
public class IdLifecycleTracker {

    private static final String KEY_PREFIX = "distid:lifecycle:";
    private static final String INDEX_PREFIX = "distid:trace:";
    private static final String BIZ_INDEX_PREFIX = "distid:biz:";
    private static final long DEFAULT_TTL_HOURS = 72;

    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final boolean trackingEnabled;

    public IdLifecycleTracker(StringRedisTemplate redis, boolean trackingEnabled) {
        this.redis = redis;
        this.trackingEnabled = trackingEnabled;
        this.objectMapper = new ObjectMapper();
    }

    public void onGenerated(long id, String readableId, String mode, String bizTag, TraceContext context) {
        recordEvent(id, readableId, IdLifecycleEvent.Stage.GENERATED, mode, bizTag, context, "ID generated");
    }

    public void onAssigned(long id, String readableId, String mode, String bizTag, TraceContext context) {
        recordEvent(id, readableId, IdLifecycleEvent.Stage.ASSIGNED, mode, bizTag, context, "ID assigned to business entity");
    }

    public void onConsumed(long id, String readableId, String mode, String bizTag, TraceContext context) {
        recordEvent(id, readableId, IdLifecycleEvent.Stage.CONSUMED, mode, bizTag, context, "ID consumed in business operation");
    }

    public void onExpired(long id, String readableId, String mode, String bizTag, TraceContext context) {
        recordEvent(id, readableId, IdLifecycleEvent.Stage.EXPIRED, mode, bizTag, context, "ID expired");
    }

    private void recordEvent(long id, String readableId, IdLifecycleEvent.Stage stage,
                              String mode, String bizTag, TraceContext context, String detail) {
        if (!trackingEnabled) return;

        try {
            IdLifecycleEvent event = IdLifecycleEvent.builder()
                    .id(id)
                    .readableId(readableId)
                    .stage(stage)
                    .bizTag(bizTag != null ? bizTag : "")
                    .mode(mode)
                    .timestamp(System.currentTimeMillis())
                    .traceId(context != null ? context.getTraceId() : "")
                    .spanId(context != null ? context.getSpanId() : "")
                    .dcCode(context != null ? context.getDcCode() : "")
                    .podName(context != null ? context.getSource() : "")
                    .detail(detail)
                    .build();

            String idKey = KEY_PREFIX + id;
            redis.opsForList().rightPush(idKey, event.toRedisValue());
            redis.expire(idKey, DEFAULT_TTL_HOURS, TimeUnit.HOURS);

            if (context != null && context.hasTrace()) {
                String traceKey = INDEX_PREFIX + context.getTraceId();
                redis.opsForSet().add(traceKey, String.valueOf(id));
                redis.expire(traceKey, DEFAULT_TTL_HOURS, TimeUnit.HOURS);
            }

            if (bizTag != null && !bizTag.isEmpty()) {
                String bizKey = BIZ_INDEX_PREFIX + bizTag;
                redis.opsForZSet().add(bizKey, String.valueOf(id), System.currentTimeMillis());
            }
        } catch (Exception e) {
            log.warn("Failed to record lifecycle event for id={}, stage={}", id, stage, e);
        }
    }

    public List<IdLifecycleEvent> getLifecycle(long id) {
        if (!trackingEnabled) return Collections.emptyList();

        try {
            String idKey = KEY_PREFIX + id;
            List<String> entries = redis.opsForList().range(idKey, 0, -1);
            if (entries == null || entries.isEmpty()) {
                return Collections.emptyList();
            }

            List<IdLifecycleEvent> events = new ArrayList<>();
            for (String entry : entries) {
                try {
                    events.add(IdLifecycleEvent.fromRedisValue(id, null, entry));
                } catch (Exception e) {
                    log.warn("Failed to parse lifecycle entry: {}", entry, e);
                }
            }
            return events;
        } catch (Exception e) {
            log.warn("Failed to get lifecycle for id={}", id, e);
            return Collections.emptyList();
        }
    }

    public Set<String> getIdsByTraceId(String traceId) {
        if (!trackingEnabled) return Collections.emptySet();

        try {
            String traceKey = INDEX_PREFIX + traceId;
            Set<String> ids = redis.opsForSet().members(traceKey);
            return ids != null ? ids : Collections.emptySet();
        } catch (Exception e) {
            log.warn("Failed to get IDs by traceId={}", traceId, e);
            return Collections.emptySet();
        }
    }

    public Set<String> getIdsByBizTag(String bizTag, long fromTimestamp, int limit) {
        if (!trackingEnabled) return Collections.emptySet();

        try {
            String bizKey = BIZ_INDEX_PREFIX + bizTag;
            Set<String> ids = redis.opsForZSet().reverseRangeByScore(bizKey, fromTimestamp, Double.MAX_VALUE);
            if (ids == null) return Collections.emptySet();
            if (ids.size() > limit) {
                return new LinkedHashSet<>(new ArrayList<>(ids).subList(0, limit));
            }
            return ids;
        } catch (Exception e) {
            log.warn("Failed to get IDs by bizTag={}", bizTag, e);
            return Collections.emptySet();
        }
    }

    public boolean isTrackingEnabled() {
        return trackingEnabled;
    }
}

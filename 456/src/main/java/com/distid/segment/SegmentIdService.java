package com.distid.segment;

import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;

import javax.annotation.PostConstruct;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
public class SegmentIdService {

    private static final String KEY_PREFIX = "distid:segment:";
    private static final long DEFAULT_STEP = 1000;

    private final JdbcTemplate jdbcTemplate;
    private final StringRedisTemplate redisTemplate;
    private final Map<String, SegmentBuffer> bufferMap = new ConcurrentHashMap<>();

    public SegmentIdService(JdbcTemplate jdbcTemplate, StringRedisTemplate redisTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        this.redisTemplate = redisTemplate;
    }

    @PostConstruct
    public void init() {
        initSchema();
        log.info("SegmentIdService initialized");
    }

    private void initSchema() {
        jdbcTemplate.execute("CREATE TABLE IF NOT EXISTS id_segment (" +
                "biz_tag VARCHAR(64) PRIMARY KEY, " +
                "max_id BIGINT NOT NULL DEFAULT 0, " +
                "step INT NOT NULL DEFAULT 1000, " +
                "version BIGINT NOT NULL DEFAULT 0, " +
                "description VARCHAR(256) DEFAULT '', " +
                "update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP" +
                ")");
        log.info("Database schema initialized for id_segment");
    }

    public long nextId(String bizTag) {
        SegmentBuffer buffer = getOrCreateBuffer(bizTag);
        return buffer.nextId();
    }

    public List<Long> nextIds(String bizTag, int count) {
        SegmentBuffer buffer = getOrCreateBuffer(bizTag);
        return buffer.nextIds(count);
    }

    private SegmentBuffer getOrCreateBuffer(String bizTag) {
        return bufferMap.computeIfAbsent(bizTag, tag -> {
            SegmentBuffer buf = new SegmentBuffer(tag) {
                @Override
                protected long fetchNextMaxIdFromStore(String bt, long currentStep) {
                    return fetchAndUpdateMaxId(bt);
                }
            };
            initBuffer(buf);
            return buf;
        });
    }

    private void initBuffer(SegmentBuffer buffer) {
        String bizTag = buffer.getBizTag();

        Long cachedMaxId = getCachedMaxId(bizTag);
        if (cachedMaxId != null) {
            Segment seg = buffer.getSegments()[0];
            seg.update(cachedMaxId, DEFAULT_STEP);
            buffer.setInitialized(true);
            log.info("Initialized buffer from Redis cache for bizTag={}, maxId={}", bizTag, cachedMaxId);
            return;
        }

        long maxId = fetchAndUpdateMaxId(bizTag);
        Segment seg = buffer.getSegments()[0];
        seg.update(maxId, DEFAULT_STEP);
        buffer.setInitialized(true);
        cacheMaxId(bizTag, maxId);
        log.info("Initialized buffer from DB for bizTag={}, maxId={}", bizTag, maxId);
    }

    private Long getCachedMaxId(String bizTag) {
        try {
            String value = redisTemplate.opsForValue().get(KEY_PREFIX + bizTag);
            if (value != null) {
                return Long.parseLong(value);
            }
        } catch (Exception e) {
            log.warn("Failed to get cached maxId from Redis for bizTag={}", bizTag, e);
        }
        return null;
    }

    private void cacheMaxId(String bizTag, long maxId) {
        try {
            redisTemplate.opsForValue().set(KEY_PREFIX + bizTag, String.valueOf(maxId));
        } catch (Exception e) {
            log.warn("Failed to cache maxId to Redis for bizTag={}", bizTag, e);
        }
    }

    private long fetchAndUpdateMaxId(String bizTag) {
        ensureBizTagExists(bizTag);

        for (int retry = 0; retry < 3; retry++) {
            try {
                Map<String, Object> row = jdbcTemplate.queryForMap(
                        "SELECT max_id, step, version FROM id_segment WHERE biz_tag = ?", bizTag);
                long currentMaxId = ((Number) row.get("max_id")).longValue();
                int step = ((Number) row.get("step")).intValue();
                long version = ((Number) row.get("version")).longValue();

                int updated = jdbcTemplate.update(
                        "UPDATE id_segment SET max_id = ?, version = version + 1, update_time = CURRENT_TIMESTAMP " +
                                "WHERE biz_tag = ? AND version = ?",
                        currentMaxId + step, bizTag, version);

                if (updated > 0) {
                    long newMaxId = currentMaxId + step;
                    cacheMaxId(bizTag, newMaxId);
                    return newMaxId;
                }
                log.info("Optimistic lock conflict for bizTag={}, retry={}", bizTag, retry);
            } catch (Exception e) {
                log.error("Failed to fetch and update maxId for bizTag={}", bizTag, e);
                if (retry == 2) {
                    throw new SegmentBufferExhaustedException("Failed to allocate segment for bizTag=" + bizTag);
                }
            }
        }
        throw new SegmentBufferExhaustedException("Failed to allocate segment after retries for bizTag=" + bizTag);
    }

    private void ensureBizTagExists(String bizTag) {
        try {
            Integer count = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM id_segment WHERE biz_tag = ?", Integer.class, bizTag);
            if (count == null || count == 0) {
                jdbcTemplate.update(
                        "INSERT INTO id_segment (biz_tag, max_id, step, version, description) VALUES (?, 0, ?, 0, ?)",
                        bizTag, DEFAULT_STEP, "Auto created");
                log.info("Auto created segment entry for bizTag={}", bizTag);
            }
        } catch (Exception e) {
            log.warn("Failed to ensure bizTag={} exists", bizTag, e);
        }
    }
}

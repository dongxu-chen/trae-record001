package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.MergeRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;

@Repository
public class MergeRequestDao {

    private static final Logger LOG = LoggerFactory.getLogger(MergeRequestDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public MergeRequestDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public void saveMergeRequest(MergeRequest request) {
        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_MERGE_REQUEST +
            " (request_id, target_user_id, source_user_ids, device_ids, reason, confidence, " +
            "evidence, status, reviewed_by, reviewed_time, review_comment, create_time, " +
            "expire_time, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        jdbcTemplate.update(sql,
            request.getRequestId(),
            request.getTargetUserId(),
            request.getSourceUserIds().toArray(new String[0]),
            request.getDeviceIds().toArray(new String[0]),
            request.getReason(),
            request.getConfidence(),
            JSON.toJSONString(request.getEvidence()),
            request.getStatus(),
            request.getReviewedBy(),
            request.getReviewedTime() != null ? request.getReviewedTime() : 0L,
            request.getReviewComment(),
            request.getCreateTime(),
            request.getExpireTime(),
            request.getSource()
        );

        saveToRedis(request);
    }

    public MergeRequest getMergeRequest(String requestId) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_MERGE_PENDING + requestId;
            String json = jedis.get(key);
            if (json != null) {
                return JSON.parseObject(json, MergeRequest.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get merge request from Redis", e);
        }

        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_MERGE_REQUEST +
            " WHERE request_id = ? ORDER BY create_time DESC LIMIT 1";

        List<MergeRequest> results = jdbcTemplate.query(sql, this::mapRow, requestId);
        return results.isEmpty() ? null : results.get(0);
    }

    public List<MergeRequest> getPendingMergeRequests(int limit, int offset) {
        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_MERGE_REQUEST +
            " WHERE status = 'pending_review' ORDER BY create_time DESC LIMIT ? OFFSET ?";

        return jdbcTemplate.query(sql, this::mapRow, limit, offset);
    }

    public List<MergeRequest> getMergeRequestsByUser(String userId, int limit, int offset) {
        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_MERGE_REQUEST +
            " WHERE target_user_id = ? OR has(source_user_ids, ?) " +
            "ORDER BY create_time DESC LIMIT ? OFFSET ?";

        return jdbcTemplate.query(sql, this::mapRow, userId, userId, limit, offset);
    }

    public void updateMergeRequestStatus(String requestId, String status, String reviewedBy,
                                         String reviewComment) {
        long reviewedTime = System.currentTimeMillis();

        String sql = "ALTER TABLE " + TrackingConstants.CLICKHOUSE_TABLE_MERGE_REQUEST +
            " UPDATE status = ?, reviewed_by = ?, reviewed_time = ?, review_comment = ? " +
            "WHERE request_id = ?";

        try {
            jdbcTemplate.update(sql, status, reviewedBy, reviewedTime, reviewComment, requestId);
        } catch (Exception e) {
            LOG.warn("ClickHouse ALTER TABLE may not be supported, using Redis only", e);
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_MERGE_PENDING + requestId;
            String json = jedis.get(key);
            if (json != null) {
                MergeRequest request = JSON.parseObject(json, MergeRequest.class);
                request.setStatus(status);
                request.setReviewedBy(reviewedBy);
                request.setReviewedTime(reviewedTime);
                request.setReviewComment(reviewComment);

                if ("approved".equals(status) || "rejected".equals(status)) {
                    jedis.del(key);
                } else {
                    jedis.setex(key, TrackingConstants.REDIS_MERGE_EXPIRE_HOURS * 3600, 
                        JSON.toJSONString(request));
                }
            }
        } catch (Exception e) {
            LOG.warn("Failed to update merge request status", e);
        }
    }

    private void saveToRedis(MergeRequest request) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_MERGE_PENDING + request.getRequestId();
            jedis.setex(key, TrackingConstants.REDIS_MERGE_EXPIRE_HOURS * 3600, 
                JSON.toJSONString(request));
        } catch (Exception e) {
            LOG.warn("Failed to save merge request to Redis", e);
        }
    }

    private MergeRequest mapRow(ResultSet rs, int rowNum) throws SQLException {
        String evidenceJson = rs.getString("evidence");
        Map<String, Object> evidence = null;
        if (evidenceJson != null && !evidenceJson.isEmpty()) {
            evidence = JSON.parseObject(evidenceJson, new TypeReference<Map<String, Object>>() {});
        }

        return MergeRequest.builder()
                .requestId(rs.getString("request_id"))
                .targetUserId(rs.getString("target_user_id"))
                .sourceUserIds(List.of((String[]) rs.getArray("source_user_ids").getArray()))
                .deviceIds(List.of((String[]) rs.getArray("device_ids").getArray()))
                .reason(rs.getString("reason"))
                .confidence(rs.getDouble("confidence"))
                .evidence(evidence)
                .status(rs.getString("status"))
                .reviewedBy(rs.getString("reviewed_by"))
                .reviewedTime(rs.getLong("reviewed_time"))
                .reviewComment(rs.getString("review_comment"))
                .createTime(rs.getLong("create_time"))
                .expireTime(rs.getLong("expire_time"))
                .source(rs.getString("source"))
                .build();
    }
}

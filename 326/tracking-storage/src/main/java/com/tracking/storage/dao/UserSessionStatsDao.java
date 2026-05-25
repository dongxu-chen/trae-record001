package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.UserSessionStats;
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

@Repository
public class UserSessionStatsDao {

    private static final Logger LOG = LoggerFactory.getLogger(UserSessionStatsDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public UserSessionStatsDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public void saveUserSessionStats(UserSessionStats stats) {
        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_USER_SESSION_STATS +
            " (user_id, anonymous_id, total_sessions, avg_session_interval, median_session_interval, " +
            "p75_session_interval, p90_session_interval, p95_session_interval, min_session_interval, " +
            "max_session_interval, dynamic_session_timeout, sample_size, last_update_time, " +
            "platform, app_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        jdbcTemplate.update(sql,
            stats.getUserId(),
            stats.getAnonymousId(),
            stats.getTotalSessions(),
            stats.getAvgSessionInterval(),
            stats.getMedianSessionInterval(),
            stats.getP75SessionInterval(),
            stats.getP90SessionInterval(),
            stats.getP95SessionInterval(),
            stats.getMinSessionInterval(),
            stats.getMaxSessionInterval(),
            stats.getDynamicSessionTimeout(),
            stats.getSampleSize(),
            stats.getLastUpdateTime(),
            stats.getPlatform(),
            stats.getAppId()
        );

        saveToRedis(stats);
    }

    public UserSessionStats getUserSessionStats(String userId, String anonymousId) {
        String keyBase = userId != null ? userId : anonymousId;
        if (keyBase == null) {
            return null;
        }

        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_SESSION_STATS + keyBase;
            String json = jedis.get(key);
            if (json != null) {
                return JSON.parseObject(json, UserSessionStats.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get user session stats from Redis", e);
        }

        StringBuilder sql = new StringBuilder();
        sql.append("SELECT * FROM ").append(TrackingConstants.CLICKHOUSE_TABLE_USER_SESSION_STATS)
           .append(" WHERE ");
        
        if (userId != null) {
            sql.append("user_id = ? ");
        } else {
            sql.append("anonymous_id = ? ");
        }
        sql.append("ORDER BY last_update_time DESC LIMIT 1");

        List<UserSessionStats> results = jdbcTemplate.query(sql.toString(), this::mapRow, keyBase);
        return results.isEmpty() ? null : results.get(0);
    }

    public Long getDynamicSessionTimeout(String userId, String anonymousId) {
        UserSessionStats stats = getUserSessionStats(userId, anonymousId);
        if (stats != null && stats.getSampleSize() >= TrackingConstants.SESSION_STATS_MIN_SAMPLES) {
            return stats.getDynamicSessionTimeout();
        }
        return TrackingConstants.SESSION_TIMEOUT_MILLIS;
    }

    private void saveToRedis(UserSessionStats stats) {
        try (Jedis jedis = jedisPool.getResource()) {
            String keyBase = stats.getUserId() != null ? stats.getUserId() : stats.getAnonymousId();
            if (keyBase != null) {
                String key = TrackingConstants.REDIS_KEY_USER_SESSION_STATS + keyBase;
                jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(stats));
            }
        } catch (Exception e) {
            LOG.warn("Failed to save user session stats to Redis", e);
        }
    }

    private UserSessionStats mapRow(ResultSet rs, int rowNum) throws SQLException {
        return UserSessionStats.builder()
                .userId(rs.getString("user_id"))
                .anonymousId(rs.getString("anonymous_id"))
                .totalSessions(rs.getInt("total_sessions"))
                .avgSessionInterval(rs.getLong("avg_session_interval"))
                .medianSessionInterval(rs.getLong("median_session_interval"))
                .p75SessionInterval(rs.getLong("p75_session_interval"))
                .p90SessionInterval(rs.getLong("p90_session_interval"))
                .p95SessionInterval(rs.getLong("p95_session_interval"))
                .minSessionInterval(rs.getLong("min_session_interval"))
                .maxSessionInterval(rs.getLong("max_session_interval"))
                .dynamicSessionTimeout(rs.getLong("dynamic_session_timeout"))
                .sampleSize(rs.getInt("sample_size"))
                .lastUpdateTime(rs.getLong("last_update_time"))
                .platform(rs.getString("platform"))
                .appId(rs.getString("app_id"))
                .build();
    }
}

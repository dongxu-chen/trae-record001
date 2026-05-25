package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.UserSessionStats;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

public class UserSessionStatsSinkFunction extends RichSinkFunction<UserSessionStats> {

    private static final Logger LOG = LoggerFactory.getLogger(UserSessionStatsSinkFunction.class);

    private final String clickHouseHost;
    private final int clickHousePort;
    private final String clickHouseDatabase;
    private final String clickHouseUsername;
    private final String clickHousePassword;
    private final String redisHost;
    private final int redisPort;
    private final String redisPassword;

    private transient Connection connection;
    private transient JedisPool jedisPool;
    private final List<UserSessionStats> batch = new ArrayList<>();
    private static final int BATCH_SIZE = 100;

    public UserSessionStatsSinkFunction(String clickHouseHost, int clickHousePort, String clickHouseDatabase,
                                         String clickHouseUsername, String clickHousePassword,
                                         String redisHost, int redisPort, String redisPassword) {
        this.clickHouseHost = clickHouseHost;
        this.clickHousePort = clickHousePort;
        this.clickHouseDatabase = clickHouseDatabase;
        this.clickHouseUsername = clickHouseUsername;
        this.clickHousePassword = clickHousePassword;
        this.redisHost = redisHost;
        this.redisPort = redisPort;
        this.redisPassword = redisPassword;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        String url = "jdbc:clickhouse://" + clickHouseHost + ":" + clickHousePort + "/" + clickHouseDatabase;
        Properties props = new Properties();
        props.setProperty("user", clickHouseUsername);
        props.setProperty("password", clickHousePassword);
        connection = DriverManager.getConnection(url, props);

        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(128);
        poolConfig.setMaxIdle(64);
        poolConfig.setMinIdle(16);
        if (redisPassword != null && !redisPassword.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000, redisPassword);
        } else {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000);
        }

        LOG.info("UserSessionStatsSinkFunction opened successfully");
    }

    @Override
    public void invoke(UserSessionStats stats, Context context) throws Exception {
        batch.add(stats);

        if (batch.size() >= BATCH_SIZE) {
            flush();
        }

        saveToRedis(stats);
    }

    private void flush() throws Exception {
        if (batch.isEmpty()) return;

        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_USER_SESSION_STATS +
            " (user_id, anonymous_id, total_sessions, avg_session_interval, median_session_interval, " +
            "p75_session_interval, p90_session_interval, p95_session_interval, min_session_interval, " +
            "max_session_interval, dynamic_session_timeout, sample_size, last_update_time, platform, app_id) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            for (UserSessionStats stats : batch) {
                pstmt.setString(1, stats.getUserId());
                pstmt.setString(2, stats.getAnonymousId());
                pstmt.setInt(3, stats.getTotalSessions());
                pstmt.setLong(4, stats.getAvgSessionInterval());
                pstmt.setLong(5, stats.getMedianSessionInterval());
                pstmt.setLong(6, stats.getP75SessionInterval());
                pstmt.setLong(7, stats.getP90SessionInterval());
                pstmt.setLong(8, stats.getP95SessionInterval());
                pstmt.setLong(9, stats.getMinSessionInterval());
                pstmt.setLong(10, stats.getMaxSessionInterval());
                pstmt.setLong(11, stats.getDynamicSessionTimeout());
                pstmt.setInt(12, stats.getSampleSize());
                pstmt.setLong(13, stats.getLastUpdateTime());
                pstmt.setString(14, stats.getPlatform());
                pstmt.setString(15, stats.getAppId());
                pstmt.addBatch();
            }
            pstmt.executeBatch();
        }

        LOG.info("Flushed {} user session stats records to ClickHouse", batch.size());
        batch.clear();
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

    @Override
    public void close() throws Exception {
        if (!batch.isEmpty()) {
            flush();
        }
        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}

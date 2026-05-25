package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.DeviceBinding;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.IdGenerator;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
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

public class DeviceBindingSinkFunction extends KeyedProcessFunction<String, TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(DeviceBindingSinkFunction.class);
    private static final int BATCH_SIZE = 100;

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
    private final List<DeviceBinding> batch = new ArrayList<>();

    public DeviceBindingSinkFunction(String clickHouseHost, int clickHousePort, String clickHouseDatabase,
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

        LOG.info("DeviceBindingSinkFunction opened successfully");
    }

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) throws Exception {
        if (event.getUserId() != null && event.getDeviceId() != null) {
            String eventType = event.getEvent();

            if (TrackingConstants.EVENT_LOGIN.equals(eventType) ||
                TrackingConstants.EVENT_REGISTER.equals(eventType) ||
                TrackingConstants.EVENT_DEVICE_BIND.equals(eventType)) {

                DeviceBinding binding = DeviceBinding.builder()
                        .id(IdGenerator.generateEventId())
                        .userId(event.getUserId())
                        .deviceId(event.getDeviceId())
                        .anonymousId(event.getAnonymousId())
                        .platform(event.getPlatform())
                        .deviceModel(event.getDeviceModel())
                        .os(event.getOs())
                        .osVersion(event.getOsVersion())
                        .appId(event.getAppId())
                        .appVersion(event.getAppVersion())
                        .bindTime(event.getTimestamp())
                        .lastActiveTime(event.getTimestamp())
                        .eventCount(1)
                        .status("active")
                        .source(event.getSource())
                        .ip(event.getIp())
                        .country(event.getCountry())
                        .province(event.getProvince())
                        .city(event.getCity())
                        .build();

                batch.add(binding);
                saveToRedis(binding);

                if (batch.size() >= BATCH_SIZE) {
                    flush();
                }
            }
        }

        collector.collect(event);
    }

    private void flush() throws Exception {
        if (batch.isEmpty()) return;

        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_DEVICE_BINDING +
            " (id, user_id, device_id, anonymous_id, platform, device_model, os, os_version, " +
            "app_id, app_version, bind_time, last_active_time, event_count, status, source, " +
            "ip, country, province, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement pstmt = connection.prepareStatement(sql)) {
            for (DeviceBinding binding : batch) {
                pstmt.setString(1, binding.getId());
                pstmt.setString(2, binding.getUserId());
                pstmt.setString(3, binding.getDeviceId());
                pstmt.setString(4, binding.getAnonymousId());
                pstmt.setString(5, binding.getPlatform());
                pstmt.setString(6, binding.getDeviceModel());
                pstmt.setString(7, binding.getOs());
                pstmt.setString(8, binding.getOsVersion());
                pstmt.setString(9, binding.getAppId());
                pstmt.setString(10, binding.getAppVersion());
                pstmt.setLong(11, binding.getBindTime());
                pstmt.setLong(12, binding.getLastActiveTime());
                pstmt.setInt(13, binding.getEventCount());
                pstmt.setString(14, binding.getStatus());
                pstmt.setString(15, binding.getSource());
                pstmt.setString(16, binding.getIp());
                pstmt.setString(17, binding.getCountry());
                pstmt.setString(18, binding.getProvince());
                pstmt.setString(19, binding.getCity());
                pstmt.addBatch();
            }
            pstmt.executeBatch();
        }

        LOG.info("Flushed {} device binding records to ClickHouse", batch.size());
        batch.clear();
    }

    private void saveToRedis(DeviceBinding binding) {
        try (Jedis jedis = jedisPool.getResource()) {
            String bindingKey = TrackingConstants.REDIS_KEY_USER_DEVICES +
                binding.getUserId() + ":" + binding.getDeviceId();
            jedis.setex(bindingKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(binding));

            String userDevicesKey = TrackingConstants.REDIS_KEY_USER_DEVICES + binding.getUserId();
            jedis.sadd(userDevicesKey, binding.getDeviceId());
            jedis.expire(userDevicesKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600);

            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + binding.getDeviceId();
            jedis.setex(deviceUserKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, binding.getUserId());
        } catch (Exception e) {
            LOG.warn("Failed to save device binding to Redis", e);
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

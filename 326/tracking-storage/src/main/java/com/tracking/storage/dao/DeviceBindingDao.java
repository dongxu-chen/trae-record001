package com.tracking.storage.dao;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.DeviceBinding;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@Repository
public class DeviceBindingDao {

    private static final Logger LOG = LoggerFactory.getLogger(DeviceBindingDao.class);

    private final JdbcTemplate jdbcTemplate;
    private final JedisPool jedisPool;

    public DeviceBindingDao(DataSource dataSource, JedisPool jedisPool) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.jedisPool = jedisPool;
    }

    public void saveDeviceBinding(DeviceBinding binding) {
        String sql = "INSERT INTO " + TrackingConstants.CLICKHOUSE_TABLE_DEVICE_BINDING +
            " (id, user_id, device_id, anonymous_id, platform, device_model, os, os_version, " +
            "app_id, app_version, bind_time, last_active_time, event_count, status, source, " +
            "ip, country, province, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        jdbcTemplate.update(sql,
            binding.getId(),
            binding.getUserId(),
            binding.getDeviceId(),
            binding.getAnonymousId(),
            binding.getPlatform(),
            binding.getDeviceModel(),
            binding.getOs(),
            binding.getOsVersion(),
            binding.getAppId(),
            binding.getAppVersion(),
            binding.getBindTime(),
            binding.getLastActiveTime(),
            binding.getEventCount(),
            binding.getStatus(),
            binding.getSource(),
            binding.getIp(),
            binding.getCountry(),
            binding.getProvince(),
            binding.getCity()
        );

        saveToRedis(binding);
    }

    public List<DeviceBinding> getDeviceBindingsByUserId(String userId) {
        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_DEVICE_BINDING +
            " WHERE user_id = ? ORDER BY last_active_time DESC";

        return jdbcTemplate.query(sql, this::mapRow, userId);
    }

    public DeviceBinding getDeviceBinding(String userId, String deviceId) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_DEVICES + userId + ":" + deviceId;
            String json = jedis.get(key);
            if (json != null) {
                return JSON.parseObject(json, DeviceBinding.class);
            }
        } catch (Exception e) {
            LOG.warn("Failed to get device binding from Redis", e);
        }

        String sql = "SELECT * FROM " + TrackingConstants.CLICKHOUSE_TABLE_DEVICE_BINDING +
            " WHERE user_id = ? AND device_id = ? ORDER BY last_active_time DESC LIMIT 1";

        List<DeviceBinding> results = jdbcTemplate.query(sql, this::mapRow, userId, deviceId);
        return results.isEmpty() ? null : results.get(0);
    }

    public void updateDeviceLastActive(String userId, String deviceId, long timestamp, int eventCount) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_DEVICES + userId + ":" + deviceId;
            String json = jedis.get(key);
            if (json != null) {
                DeviceBinding binding = JSON.parseObject(json, DeviceBinding.class);
                binding.setLastActiveTime(timestamp);
                binding.setEventCount(binding.getEventCount() + eventCount);
                jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(binding));
            }
        } catch (Exception e) {
            LOG.warn("Failed to update device binding in Redis", e);
        }
    }

    public void deactivateDevice(String userId, String deviceId) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_DEVICES + userId + ":" + deviceId;
            String json = jedis.get(key);
            if (json != null) {
                DeviceBinding binding = JSON.parseObject(json, DeviceBinding.class);
                binding.setStatus("inactive");
                jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(binding));
            }

            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + deviceId;
            jedis.del(deviceUserKey);
        } catch (Exception e) {
            LOG.warn("Failed to deactivate device", e);
        }
    }

    private void saveToRedis(DeviceBinding binding) {
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_DEVICES + 
                binding.getUserId() + ":" + binding.getDeviceId();
            jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(binding));

            String userDevicesKey = TrackingConstants.REDIS_KEY_USER_DEVICES + binding.getUserId();
            jedis.sadd(userDevicesKey, binding.getDeviceId());
            jedis.expire(userDevicesKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600);

            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + binding.getDeviceId();
            jedis.setex(deviceUserKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, binding.getUserId());
        } catch (Exception e) {
            LOG.warn("Failed to save device binding to Redis", e);
        }
    }

    private DeviceBinding mapRow(ResultSet rs, int rowNum) throws SQLException {
        return DeviceBinding.builder()
                .id(rs.getString("id"))
                .userId(rs.getString("user_id"))
                .deviceId(rs.getString("device_id"))
                .anonymousId(rs.getString("anonymous_id"))
                .platform(rs.getString("platform"))
                .deviceModel(rs.getString("device_model"))
                .os(rs.getString("os"))
                .osVersion(rs.getString("os_version"))
                .appId(rs.getString("app_id"))
                .appVersion(rs.getString("app_version"))
                .bindTime(rs.getLong("bind_time"))
                .lastActiveTime(rs.getLong("last_active_time"))
                .eventCount(rs.getInt("event_count"))
                .status(rs.getString("status"))
                .source(rs.getString("source"))
                .ip(rs.getString("ip"))
                .country(rs.getString("country"))
                .province(rs.getString("province"))
                .city(rs.getString("city"))
                .build();
    }
}

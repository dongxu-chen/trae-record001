package com.tracking.storage.service;

import com.tracking.common.constant.TrackingConstants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

@Service
public class UserMappingService {

    private static final Logger LOG = LoggerFactory.getLogger(UserMappingService.class);

    private final JedisPool jedisPool;

    public UserMappingService(JedisPool jedisPool) {
        this.jedisPool = jedisPool;
    }

    public String getUserId(String anonymousId) {
        if (anonymousId == null) {
            return null;
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_MAPPING + anonymousId;
            return jedis.get(key);
        } catch (Exception e) {
            LOG.warn("Failed to get user mapping for anonymousId: {}", anonymousId, e);
            return null;
        }
    }

    public void saveUserMapping(String anonymousId, String userId) {
        if (anonymousId == null || userId == null) {
            return;
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_MAPPING + anonymousId;
            jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, userId);
            LOG.debug("Saved user mapping: {} -> {}", anonymousId, userId);
        } catch (Exception e) {
            LOG.warn("Failed to save user mapping: {} -> {}", anonymousId, userId, e);
        }
    }

    public String getAnonymousIdByDevice(String deviceId) {
        if (deviceId == null) {
            return null;
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_DEVICE_ANONYMOUS + deviceId;
            return jedis.get(key);
        } catch (Exception e) {
            LOG.warn("Failed to get anonymousId for deviceId: {}", deviceId, e);
            return null;
        }
    }

    public void saveDeviceAnonymousMapping(String deviceId, String anonymousId) {
        if (deviceId == null || anonymousId == null) {
            return;
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_DEVICE_ANONYMOUS + deviceId;
            jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, anonymousId);
        } catch (Exception e) {
            LOG.warn("Failed to save device mapping: {} -> {}", deviceId, anonymousId, e);
        }
    }

    public void deleteMapping(String anonymousId) {
        if (anonymousId == null) {
            return;
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String key = TrackingConstants.REDIS_KEY_USER_MAPPING + anonymousId;
            jedis.del(key);
        } catch (Exception e) {
            LOG.warn("Failed to delete mapping for anonymousId: {}", anonymousId, e);
        }
    }
}

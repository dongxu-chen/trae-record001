package com.tracking.flink.function;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.DeviceBinding;
import com.tracking.common.model.MergeRequest;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.IdGenerator;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.util.*;

public class UserIdentifyFunction extends ProcessFunction<TrackEvent, TrackEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(UserIdentifyFunction.class);

    private final String redisHost;
    private final int redisPort;
    private final String redisPassword;
    private transient JedisPool jedisPool;

    public UserIdentifyFunction(String redisHost, int redisPort, String redisPassword) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
        this.redisPassword = redisPassword;
    }

    @Override
    public void open(Configuration parameters) {
        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(128);
        poolConfig.setMaxIdle(64);
        poolConfig.setMinIdle(16);
        poolConfig.setTestOnBorrow(true);
        poolConfig.setTestOnReturn(true);
        poolConfig.setTestWhileIdle(true);

        if (redisPassword != null && !redisPassword.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000, redisPassword);
        } else {
            jedisPool = new JedisPool(poolConfig, redisHost, redisPort, 2000);
        }
    }

    @Override
    public void processElement(TrackEvent event, Context context, Collector<TrackEvent> collector) {
        try (Jedis jedis = jedisPool.getResource()) {
            String identifiedUserId = identifyUser(event, jedis);

            if (identifiedUserId != null) {
                event.setUserId(identifiedUserId);
            }

            if (event.getUserId() != null && event.getAnonymousId() != null) {
                storeUserMapping(event.getAnonymousId(), event.getUserId(), jedis);
            }

            if (event.getDeviceId() != null && event.getAnonymousId() != null) {
                storeDeviceAnonymousMapping(event.getDeviceId(), event.getAnonymousId(), jedis);
            }

            if (event.getUserId() != null && event.getDeviceId() != null) {
                manageDeviceBinding(event, jedis);
                checkCrossDeviceMerge(event, jedis, collector);
            }

            collector.collect(event);
        } catch (Exception e) {
            LOG.error("Error in user identification", e);
            collector.collect(event);
        }
    }

    private String identifyUser(TrackEvent event, Jedis jedis) {
        if (event.getUserId() != null && !IdGenerator.isAnonymousId(event.getUserId())) {
            return event.getUserId();
        }

        String userIdFromDevice = null;
        if (event.getDeviceId() != null) {
            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + event.getDeviceId();
            userIdFromDevice = jedis.get(deviceUserKey);
        }

        String userIdFromAnonymous = null;
        if (event.getAnonymousId() != null) {
            String key = TrackingConstants.REDIS_KEY_USER_MAPPING + event.getAnonymousId();
            userIdFromAnonymous = jedis.get(key);
        }

        if (userIdFromDevice != null) {
            return userIdFromDevice;
        }
        if (userIdFromAnonymous != null) {
            return userIdFromAnonymous;
        }

        if (event.getDeviceId() != null) {
            String deviceKey = TrackingConstants.REDIS_KEY_DEVICE_ANONYMOUS + event.getDeviceId();
            String anonymousId = jedis.get(deviceKey);
            if (anonymousId != null) {
                String userKey = TrackingConstants.REDIS_KEY_USER_MAPPING + anonymousId;
                return jedis.get(userKey);
            }
        }

        return null;
    }

    private void manageDeviceBinding(TrackEvent event, Jedis jedis) {
        try {
            String userId = event.getUserId();
            String deviceId = event.getDeviceId();

            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + deviceId;
            String existingUserId = jedis.get(deviceUserKey);

            if (existingUserId == null) {
                jedis.setex(deviceUserKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, userId);
            }

            String userDevicesKey = TrackingConstants.REDIS_KEY_USER_DEVICES + userId;
            jedis.sadd(userDevicesKey, deviceId);
            jedis.expire(userDevicesKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600);

            DeviceBinding binding = DeviceBinding.builder()
                    .id(IdGenerator.generateEventId())
                    .userId(userId)
                    .deviceId(deviceId)
                    .anonymousId(event.getAnonymousId())
                    .platform(event.getPlatform())
                    .deviceModel(event.getDeviceModel())
                    .os(event.getOs())
                    .osVersion(event.getOsVersion())
                    .appId(event.getAppId())
                    .appVersion(event.getAppVersion())
                    .bindTime(System.currentTimeMillis())
                    .lastActiveTime(event.getTimestamp())
                    .eventCount(1)
                    .status("active")
                    .source(event.getSource())
                    .ip(event.getIp())
                    .country(event.getCountry())
                    .province(event.getProvince())
                    .city(event.getCity())
                    .build();

            String bindingKey = TrackingConstants.REDIS_KEY_USER_DEVICES + userId + ":" + deviceId;
            jedis.setex(bindingKey, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, JSON.toJSONString(binding));

            LOG.debug("Device binding created: user={}, device={}", userId, deviceId);
        } catch (Exception e) {
            LOG.warn("Failed to manage device binding", e);
        }
    }

    private void checkCrossDeviceMerge(TrackEvent event, Jedis jedis, Collector<TrackEvent> collector) {
        try {
            String deviceId = event.getDeviceId();
            String currentUserId = event.getUserId();

            String deviceUserKey = TrackingConstants.REDIS_KEY_DEVICE_USER + deviceId;
            String existingUserId = jedis.get(deviceUserKey);

            if (existingUserId != null && !existingUserId.equals(currentUserId)) {
                Set<String> currentUserDevices = jedis.smembers(TrackingConstants.REDIS_KEY_USER_DEVICES + currentUserId);
                Set<String> existingUserDevices = jedis.smembers(TrackingConstants.REDIS_KEY_USER_DEVICES + existingUserId);

                int commonDevices = 0;
                for (String dev : currentUserDevices) {
                    if (existingUserDevices.contains(dev)) {
                        commonDevices++;
                    }
                }

                if (commonDevices >= TrackingConstants.DEVICE_MERGE_THRESHOLD) {
                    triggerMergeRequest(existingUserId, currentUserId, 
                        currentUserDevices, existingUserDevices, event, jedis, collector);
                } else {
                    generateCrossDeviceEvent(existingUserId, currentUserId, deviceId, 
                        commonDevices, event, collector);
                }
            }
        } catch (Exception e) {
            LOG.warn("Failed to check cross device merge", e);
        }
    }

    private void triggerMergeRequest(String sourceUserId, String targetUserId,
                                      Set<String> sourceDevices, Set<String> targetDevices,
                                      TrackEvent event, Jedis jedis, Collector<TrackEvent> collector) {
        String mergeRequestId = "merge_" + System.currentTimeMillis() + "_" + 
            IdGenerator.generateShortUUID();

        Map<String, Object> evidence = new HashMap<>();
        evidence.put("sourceUserId", sourceUserId);
        evidence.put("targetUserId", targetUserId);
        evidence.put("sourceDevices", sourceDevices);
        evidence.put("targetDevices", targetDevices);
        evidence.put("triggerEvent", event.getEvent());
        evidence.put("triggerDevice", event.getDeviceId());
        evidence.put("commonDeviceCount", countCommonDevices(sourceDevices, targetDevices));

        double confidence = calculateMergeConfidence(sourceDevices, targetDevices);

        MergeRequest mergeRequest = MergeRequest.builder()
                .requestId(mergeRequestId)
                .targetUserId(targetUserId)
                .sourceUserIds(Collections.singletonList(sourceUserId))
                .deviceIds(new ArrayList<>(targetDevices))
                .reason("cross_device_detection")
                .confidence(confidence)
                .evidence(evidence)
                .status("pending_review")
                .createTime(System.currentTimeMillis())
                .expireTime(System.currentTimeMillis() + 
                    TrackingConstants.REDIS_MERGE_EXPIRE_HOURS * 3600 * 1000L)
                .source(event.getSource())
                .build();

        String mergeKey = TrackingConstants.REDIS_KEY_MERGE_PENDING + mergeRequestId;
        jedis.setex(mergeKey, TrackingConstants.REDIS_MERGE_EXPIRE_HOURS * 3600, 
            JSON.toJSONString(mergeRequest));

        TrackEvent mergeEvent = TrackEvent.builder()
                .id(IdGenerator.generateEventId())
                .event(TrackingConstants.EVENT_CROSS_DEVICE_DETECTED)
                .timestamp(System.currentTimeMillis())
                .receiveTime(System.currentTimeMillis())
                .anonymousId(event.getAnonymousId())
                .userId(targetUserId)
                .sessionId(event.getSessionId())
                .deviceId(event.getDeviceId())
                .platform(event.getPlatform())
                .appId(event.getAppId())
                .source(event.getSource())
                .build();

        mergeEvent.addProperty("merge_request_id", mergeRequestId);
        mergeEvent.addProperty("source_user_id", sourceUserId);
        mergeEvent.addProperty("target_user_id", targetUserId);
        mergeEvent.addProperty("confidence", confidence);
        mergeEvent.addProperty("device_count", sourceDevices.size() + targetDevices.size());
        mergeEvent.addProperty("common_device_count", countCommonDevices(sourceDevices, targetDevices));

        collector.collect(mergeEvent);

        LOG.info("Cross-device merge request created: {}, confidence: {}", mergeRequestId, confidence);
    }

    private void generateCrossDeviceEvent(String existingUserId, String currentUserId,
                                           String deviceId, int commonDevices,
                                           TrackEvent event, Collector<TrackEvent> collector) {
        TrackEvent crossDeviceEvent = TrackEvent.builder()
                .id(IdGenerator.generateEventId())
                .event(TrackingConstants.EVENT_DEVICE_BIND)
                .timestamp(System.currentTimeMillis())
                .receiveTime(System.currentTimeMillis())
                .anonymousId(event.getAnonymousId())
                .userId(currentUserId)
                .sessionId(event.getSessionId())
                .deviceId(deviceId)
                .platform(event.getPlatform())
                .appId(event.getAppId())
                .source(event.getSource())
                .build();

        crossDeviceEvent.addProperty("previous_user_id", existingUserId);
        crossDeviceEvent.addProperty("current_user_id", currentUserId);
        crossDeviceEvent.addProperty("device_id", deviceId);
        crossDeviceEvent.addProperty("common_device_count", commonDevices);

        collector.collect(crossDeviceEvent);

        LOG.debug("Device bind event: user={}, device={}, previousUser={}", 
            currentUserId, deviceId, existingUserId);
    }

    private int countCommonDevices(Set<String> devices1, Set<String> devices2) {
        int count = 0;
        for (String dev : devices1) {
            if (devices2.contains(dev)) {
                count++;
            }
        }
        return count;
    }

    private double calculateMergeConfidence(Set<String> devices1, Set<String> devices2) {
        int common = countCommonDevices(devices1, devices2);
        int total = devices1.size() + devices2.size() - common;
        if (total == 0) return 0.0;

        double deviceSimilarity = (double) common / Math.min(devices1.size(), devices2.size());
        double baseConfidence = 0.5 + (deviceSimilarity * 0.5);

        return Math.min(0.99, Math.max(0.1, baseConfidence));
    }

    private void storeUserMapping(String anonymousId, String userId, Jedis jedis) {
        String key = TrackingConstants.REDIS_KEY_USER_MAPPING + anonymousId;
        jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, userId);
    }

    private void storeDeviceAnonymousMapping(String deviceId, String anonymousId, Jedis jedis) {
        String key = TrackingConstants.REDIS_KEY_DEVICE_ANONYMOUS + deviceId;
        jedis.setex(key, TrackingConstants.REDIS_EXPIRE_HOURS * 3600, anonymousId);
    }

    @Override
    public void close() {
        if (jedisPool != null) {
            jedisPool.close();
        }
    }
}

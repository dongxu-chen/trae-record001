package com.riskcontrol.redis.service;

import com.riskcontrol.common.model.DeviceFingerprint;
import com.riskcontrol.common.utils.DeviceFingerprintUtil;
import org.redisson.api.RMap;
import org.redisson.api.RSet;
import org.redisson.api.RedissonClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

@Service
public class DeviceFingerprintService {

    private static final Logger logger = LoggerFactory.getLogger(DeviceFingerprintService.class);

    private static final String DEVICE_FINGERPRINT_MAP = "risk:device:fingerprint:";
    private static final String DEVICE_ACCOUNT_SET = "risk:device:accounts:";
    private static final long DEVICE_EXPIRE_DAYS = 90;

    private final RedissonClient redissonClient;

    @Autowired
    public DeviceFingerprintService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public DeviceFingerprint saveDeviceFingerprint(DeviceFingerprint fingerprint) {
        if (fingerprint.getDeviceId() == null || fingerprint.getDeviceId().isEmpty()) {
            String deviceId = DeviceFingerprintUtil.generateDeviceId(fingerprint);
            fingerprint.setDeviceId(deviceId);
        }

        String key = DEVICE_FINGERPRINT_MAP + fingerprint.getDeviceId();
        RMap<String, Object> deviceMap = redissonClient.getMap(key);

        long now = System.currentTimeMillis();
        if (fingerprint.getFirstSeenTimestamp() == 0) {
            DeviceFingerprint existing = getDeviceFingerprint(fingerprint.getDeviceId());
            if (existing != null) {
                fingerprint.setFirstSeenTimestamp(existing.getFirstSeenTimestamp());
                fingerprint.setAssociationCount(existing.getAssociationCount());
            } else {
                fingerprint.setFirstSeenTimestamp(now);
            }
        }
        fingerprint.setLastSeenTimestamp(now);

        deviceMap.put("deviceId", fingerprint.getDeviceId());
        deviceMap.put("userAgent", fingerprint.getUserAgent());
        deviceMap.put("platform", fingerprint.getPlatform());
        deviceMap.put("browser", fingerprint.getBrowser());
        deviceMap.put("os", fingerprint.getOs());
        deviceMap.put("screenResolution", fingerprint.getScreenResolution());
        deviceMap.put("language", fingerprint.getLanguage());
        deviceMap.put("timezone", fingerprint.getTimezone());
        deviceMap.put("canvasFingerprint", fingerprint.getCanvasFingerprint());
        deviceMap.put("webglFingerprint", fingerprint.getWebglFingerprint());
        deviceMap.put("fontsFingerprint", fingerprint.getFontsFingerprint());
        deviceMap.put("ipAddress", fingerprint.getIpAddress());
        deviceMap.put("hardwareConcurrency", fingerprint.getHardwareConcurrency());
        deviceMap.put("deviceMemory", fingerprint.getDeviceMemory());
        deviceMap.put("firstSeenTimestamp", fingerprint.getFirstSeenTimestamp());
        deviceMap.put("lastSeenTimestamp", fingerprint.getLastSeenTimestamp());
        deviceMap.put("associationCount", fingerprint.getAssociationCount());

        deviceMap.expire(DEVICE_EXPIRE_DAYS, TimeUnit.DAYS);

        logger.debug("Saved device fingerprint: {}", fingerprint.getDeviceId());
        return fingerprint;
    }

    public DeviceFingerprint getDeviceFingerprint(String deviceId) {
        if (deviceId == null || deviceId.isEmpty()) {
            return null;
        }

        String key = DEVICE_FINGERPRINT_MAP + deviceId;
        RMap<String, Object> deviceMap = redissonClient.getMap(key);

        if (deviceMap.isEmpty()) {
            return null;
        }

        return DeviceFingerprint.builder()
                .deviceId((String) deviceMap.get("deviceId"))
                .userAgent((String) deviceMap.get("userAgent"))
                .platform((String) deviceMap.get("platform"))
                .browser((String) deviceMap.get("browser"))
                .os((String) deviceMap.get("os"))
                .screenResolution((String) deviceMap.get("screenResolution"))
                .language((String) deviceMap.get("language"))
                .timezone((String) deviceMap.get("timezone"))
                .canvasFingerprint((String) deviceMap.get("canvasFingerprint"))
                .webglFingerprint((String) deviceMap.get("webglFingerprint"))
                .fontsFingerprint((String) deviceMap.get("fontsFingerprint"))
                .ipAddress((String) deviceMap.get("ipAddress"))
                .hardwareConcurrency((String) deviceMap.get("hardwareConcurrency"))
                .deviceMemory((String) deviceMap.get("deviceMemory"))
                .firstSeenTimestamp(deviceMap.get("firstSeenTimestamp") != null ?
                        (Long) deviceMap.get("firstSeenTimestamp") : 0)
                .lastSeenTimestamp(deviceMap.get("lastSeenTimestamp") != null ?
                        (Long) deviceMap.get("lastSeenTimestamp") : 0)
                .associationCount(deviceMap.get("associationCount") != null ?
                        (Integer) deviceMap.get("associationCount") : 0)
                .build();
    }

    public void associateDeviceWithAccount(String deviceId, String userId) {
        if (deviceId == null || userId == null) {
            return;
        }

        String setKey = DEVICE_ACCOUNT_SET + deviceId;
        RSet<String> accountSet = redissonClient.getSet(setKey);
        accountSet.add(userId);
        accountSet.expire(DEVICE_EXPIRE_DAYS, TimeUnit.DAYS);

        String deviceKey = DEVICE_FINGERPRINT_MAP + deviceId;
        RMap<String, Object> deviceMap = redissonClient.getMap(deviceKey);
        int count = accountSet.size();
        deviceMap.put("associationCount", count);

        logger.debug("Associated device {} with account {}, total associations: {}",
                deviceId, userId, count);
    }

    public int getDeviceAssociationCount(String deviceId) {
        if (deviceId == null) {
            return 0;
        }
        String setKey = DEVICE_ACCOUNT_SET + deviceId;
        RSet<String> accountSet = redissonClient.getSet(setKey);
        return accountSet.size();
    }

    public boolean isNewDevice(String deviceId) {
        DeviceFingerprint fingerprint = getDeviceFingerprint(deviceId);
        if (fingerprint == null) {
            return true;
        }
        long oneDayMs = 24 * 60 * 60 * 1000L;
        return (System.currentTimeMillis() - fingerprint.getFirstSeenTimestamp()) < oneDayMs;
    }
}

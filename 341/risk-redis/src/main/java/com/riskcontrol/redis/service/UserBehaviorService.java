package com.riskcontrol.redis.service;

import com.riskcontrol.common.model.UserBehaviorProfile;
import org.redisson.api.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class UserBehaviorService {

    private static final Logger logger = LoggerFactory.getLogger(UserBehaviorService.class);

    private static final String USER_PROFILE_MAP = "risk:user:profile:";
    private static final String USER_LOGIN_IP_SET = "risk:user:login_ips:";
    private static final String USER_LOGIN_DEVICE_SET = "risk:user:login_devices:";
    private static final String USER_LOGIN_HOURS_KEY = "risk:user:login_hours:";
    private static final String USER_LOGIN_COUNTRIES = "risk:user:login_countries:";
    private static final String USER_LOGIN_TIMES = "risk:user:login_times:";
    private static final String USER_FAILED_LOGINS = "risk:user:failed_logins:";
    private static final long PROFILE_EXPIRE_DAYS = 365;

    private final RedissonClient redissonClient;

    @Autowired
    public UserBehaviorService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public void recordLogin(String userId, String ipAddress, String deviceId,
                            String country, long timestamp) {
        if (userId == null) return;

        RSet<String> ipSet = redissonClient.getSet(USER_LOGIN_IP_SET + userId);
        ipSet.add(ipAddress);
        ipSet.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        RSet<String> deviceSet = redissonClient.getSet(USER_LOGIN_DEVICE_SET + userId);
        deviceSet.add(deviceId);
        deviceSet.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        if (country != null) {
            RSet<String> countrySet = redissonClient.getSet(USER_LOGIN_COUNTRIES + userId);
            countrySet.add(country);
            countrySet.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);
        }

        int hour = (int) ((timestamp / 3600000) % 24);
        RMap<String, Integer> hoursMap = redissonClient.getMap(USER_LOGIN_HOURS_KEY + userId);
        String hourKey = String.valueOf(hour);
        hoursMap.put(hourKey, hoursMap.getOrDefault(hourKey, 0) + 1);
        hoursMap.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        RDeque<Long> loginTimes = redissonClient.getDeque(USER_LOGIN_TIMES + userId);
        loginTimes.addFirst(timestamp);
        while (loginTimes.size() > 100) {
            loginTimes.removeLast();
        }
        loginTimes.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        updateTotalLoginCount(userId);

        logger.debug("Recorded login for user {} from IP {}, device {}", userId, ipAddress, deviceId);
    }

    public void recordFailedLogin(String userId, String ipAddress) {
        if (userId == null) return;

        String key = USER_FAILED_LOGINS + userId + ":" + ipAddress;
        RAtomicLong counter = redissonClient.getAtomicLong(key);
        counter.incrementAndGet();
        counter.expire(1, TimeUnit.HOURS);

        logger.debug("Recorded failed login for user {} from IP {}", userId, ipAddress);
    }

    public int getFailedLoginAttempts(String userId, String ipAddress) {
        if (userId == null || ipAddress == null) return 0;

        String key = USER_FAILED_LOGINS + userId + ":" + ipAddress;
        RAtomicLong counter = redissonClient.getAtomicLong(key);
        return (int) counter.get();
    }

    public void resetFailedLoginAttempts(String userId, String ipAddress) {
        if (userId == null || ipAddress == null) return;

        String key = USER_FAILED_LOGINS + userId + ":" + ipAddress;
        redissonClient.getAtomicLong(key).delete();
    }

    public UserBehaviorProfile getUserBehaviorProfile(String userId) {
        if (userId == null) return null;

        RSet<String> ipSet = redissonClient.getSet(USER_LOGIN_IP_SET + userId);
        RSet<String> deviceSet = redissonClient.getSet(USER_LOGIN_DEVICE_SET + userId);
        RSet<String> countrySet = redissonClient.getSet(USER_LOGIN_COUNTRIES + userId);
        RMap<String, Integer> hoursMap = redissonClient.getMap(USER_LOGIN_HOURS_KEY + userId);
        RMap<String, Object> profileMap = redissonClient.getMap(USER_PROFILE_MAP + userId);

        int[] loginHours = calculateUsualLoginHours(hoursMap);

        long accountCreationTimestamp = profileMap.get("accountCreationTimestamp") != null ?
                (Long) profileMap.get("accountCreationTimestamp") : System.currentTimeMillis();
        long lastActiveTimestamp = profileMap.get("lastActiveTimestamp") != null ?
                (Long) profileMap.get("lastActiveTimestamp") : System.currentTimeMillis();
        int fraudFlagCount = profileMap.get("fraudFlagCount") != null ?
                (Integer) profileMap.get("fraudFlagCount") : 0;
        int passwordChangeCount = profileMap.get("passwordChangeCount") != null ?
                (Integer) profileMap.get("passwordChangeCount") : 0;
        int totalLoginCount = profileMap.get("totalLoginCount") != null ?
                (Integer) profileMap.get("totalLoginCount") : 0;
        int failedLoginCount = profileMap.get("failedLoginCount") != null ?
                (Integer) profileMap.get("failedLoginCount") : 0;

        return UserBehaviorProfile.builder()
                .userId(userId)
                .commonIpAddresses(new HashSet<>(ipSet.readAll()))
                .commonDeviceIds(new HashSet<>(deviceSet.readAll()))
                .commonCountries(new HashSet<>(countrySet.readAll()))
                .usualLoginStartHour(loginHours[0])
                .usualLoginEndHour(loginHours[1])
                .totalLoginCount(totalLoginCount)
                .failedLoginCount(failedLoginCount)
                .passwordChangeCount(passwordChangeCount)
                .accountCreationTimestamp(accountCreationTimestamp)
                .lastActiveTimestamp(lastActiveTimestamp)
                .fraudFlagCount(fraudFlagCount)
                .build();
    }

    private int[] calculateUsualLoginHours(RMap<String, Integer> hoursMap) {
        if (hoursMap == null || hoursMap.isEmpty()) {
            return new int[]{8, 22};
        }

        Map<Integer, Integer> hours = hoursMap.entrySet().stream()
                .collect(Collectors.toMap(
                        e -> Integer.parseInt(e.getKey()),
                        Map.Entry::getValue
                ));

        int totalLogins = hours.values().stream().mapToInt(Integer::intValue).sum();
        int threshold = totalLogins / 24;

        List<Integer> activeHours = hours.entrySet().stream()
                .filter(e -> e.getValue() > threshold)
                .map(Map.Entry::getKey)
                .sorted()
                .collect(Collectors.toList());

        if (activeHours.isEmpty()) {
            return new int[]{8, 22};
        }

        int startHour = activeHours.get(0);
        int endHour = activeHours.get(activeHours.size() - 1) + 1;

        return new int[]{startHour, Math.min(endHour, 24)};
    }

    private void updateTotalLoginCount(String userId) {
        RMap<String, Object> profileMap = redissonClient.getMap(USER_PROFILE_MAP + userId);
        int currentCount = profileMap.get("totalLoginCount") != null ?
                (Integer) profileMap.get("totalLoginCount") : 0;
        profileMap.put("totalLoginCount", currentCount + 1);
        profileMap.put("lastActiveTimestamp", System.currentTimeMillis());
        profileMap.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);
    }

    public void recordPasswordChange(String userId) {
        if (userId == null) return;

        RMap<String, Object> profileMap = redissonClient.getMap(USER_PROFILE_MAP + userId);
        int currentCount = profileMap.get("passwordChangeCount") != null ?
                (Integer) profileMap.get("passwordChangeCount") : 0;
        profileMap.put("passwordChangeCount", currentCount + 1);
        profileMap.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        logger.debug("Recorded password change for user {}", userId);
    }

    public void recordFraudFlag(String userId, String reason) {
        if (userId == null) return;

        RMap<String, Object> profileMap = redissonClient.getMap(USER_PROFILE_MAP + userId);
        int currentCount = profileMap.get("fraudFlagCount") != null ?
                (Integer) profileMap.get("fraudFlagCount") : 0;
        profileMap.put("fraudFlagCount", currentCount + 1);
        profileMap.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);

        logger.info("Recorded fraud flag for user {}, reason: {}, total flags: {}",
                userId, reason, currentCount + 1);
    }

    public void initializeUserProfile(String userId) {
        if (userId == null) return;

        RMap<String, Object> profileMap = redissonClient.getMap(USER_PROFILE_MAP + userId);
        if (!profileMap.containsKey("accountCreationTimestamp")) {
            profileMap.put("accountCreationTimestamp", System.currentTimeMillis());
            profileMap.put("totalLoginCount", 0);
            profileMap.put("failedLoginCount", 0);
            profileMap.put("passwordChangeCount", 0);
            profileMap.put("fraudFlagCount", 0);
            profileMap.expire(PROFILE_EXPIRE_DAYS, TimeUnit.DAYS);
            logger.debug("Initialized user profile for {}", userId);
        }
    }

    public long getLastLoginTimestamp(String userId) {
        if (userId == null) return 0;

        RDeque<Long> loginTimes = redissonClient.getDeque(USER_LOGIN_TIMES + userId);
        if (loginTimes.isEmpty()) {
            return 0;
        }
        Long first = loginTimes.peekFirst();
        return first != null ? first : 0;
    }

    public String getLastLoginIp(String userId) {
        if (userId == null) return null;

        RSet<String> ipSet = redissonClient.getSet(USER_LOGIN_IP_SET + userId);
        Iterator<String> iterator = ipSet.iterator();
        return iterator.hasNext() ? iterator.next() : null;
    }

    public String getLastLoginDeviceId(String userId) {
        if (userId == null) return null;

        RSet<String> deviceSet = redissonClient.getSet(USER_LOGIN_DEVICE_SET + userId);
        Iterator<String> iterator = deviceSet.iterator();
        return iterator.hasNext() ? iterator.next() : null;
    }
}

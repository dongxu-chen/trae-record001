package com.coupon.security.service;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

@Slf4j
@Service
public class CouponAntiFraudService {

    private static final String USER_FREQUENCY_KEY = "antifraud:user:freq:";
    private static final String IP_FREQUENCY_KEY = "antifraud:ip:freq:";
    private static final String DEVICE_FREQUENCY_KEY = "antifraud:device:freq:";
    private static final String IP_USER_MAPPING_KEY = "antifraud:ip:users:";
    private static final String DEVICE_USER_MAPPING_KEY = "antifraud:device:users:";
    private static final String BLACKLIST_KEY = "antifraud:blacklist:";
    private static final String RISK_SCORE_KEY = "antifraud:risk:";
    private static final String SUSPECT_BATCH_KEY = "antifraud:suspect:batch:";

    private static final DateTimeFormatter MINUTE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
    private static final DateTimeFormatter HOUR_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHH");

    private final StringRedisTemplate redisTemplate;

    @Value("${coupon.antifraud.max-coupons-per-user-per-hour:3}")
    private int maxCouponsPerUserPerHour;

    @Value("${coupon.antifraud.max-coupons-per-user-per-day:10}")
    private int maxCouponsPerUserPerDay;

    @Value("${coupon.antifraud.max-users-per-ip:5}")
    private int maxUsersPerIp;

    @Value("${coupon.antifraud.max-users-per-device:3}")
    private int maxUsersPerDevice;

    @Value("${coupon.antifraud.min-interval-ms:1000}")
    private long minIntervalMs;

    @Value("${coupon.antifraud.risk-threshold:70}")
    private int riskThreshold;

    private final List<Pattern> suspiciousPhonePatterns = Arrays.asList(
            Pattern.compile("^13[0-9]{9}$"),
            Pattern.compile("^1[45789][0-9]{9}$")
    );

    public CouponAntiFraudService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public FraudCheckResult performFraudCheck(String userId, String clientIp, String deviceId) {
        FraudCheckResult result = FraudCheckResult.builder()
                .userId(userId)
                .checkTime(LocalDateTime.now())
                .passed(true)
                .riskScore(0)
                .risks(new ArrayList<>())
                .build();

        try {
            checkUserFrequency(userId, result);
            checkRequestInterval(userId, result);

            if (clientIp != null && !clientIp.isEmpty()) {
                checkIpClustering(clientIp, userId, result);
                checkIpFrequency(clientIp, result);
            }

            if (deviceId != null && !deviceId.isEmpty()) {
                checkDeviceClustering(deviceId, userId, result);
                checkDeviceEmulator(deviceId, result);
            }

            checkUserPattern(userId, result);
            checkAccountAge(userId, result);
            checkBlacklist(userId, clientIp, deviceId, result);

            calculateFinalRiskScore(result);

            if (result.getRiskScore() >= riskThreshold) {
                result.setPassed(false);
                result.setBlockReason("高风险用户，风险分数: " + result.getRiskScore());
                log.warn("Blocked high risk user {}: score={}, risks={}",
                        userId, result.getRiskScore(), result.getRisks());

                if (result.getRiskScore() >= 90) {
                    addToBlacklist(userId, clientIp, deviceId, 24);
                }
            }

            recordCheckResult(userId, result);

        } catch (Exception e) {
            log.error("Failed to perform fraud check for user: {}", userId, e);
        }

        return result;
    }

    private void checkUserFrequency(String userId, FraudCheckResult result) {
        String hourKey = USER_FREQUENCY_KEY + "hour:" + LocalDateTime.now().format(HOUR_FORMATTER) + ":" + userId;
        String dayKey = USER_FREQUENCY_KEY + "day:" + userId;

        try {
            Long hourCount = redisTemplate.opsForValue().increment(hourKey);
            Long dayCount = redisTemplate.opsForValue().increment(dayKey);

            if (hourCount != null && hourCount == 1) {
                redisTemplate.expire(hourKey, 1, TimeUnit.HOURS);
            }
            if (dayCount != null && dayCount == 1) {
                redisTemplate.expire(dayKey, 1, TimeUnit.DAYS);
            }

            if (hourCount != null && hourCount > maxCouponsPerUserPerHour) {
                result.getRisks().add(RiskItem.builder()
                        .type("USER_FREQUENCY_HOURLY")
                        .level("HIGH")
                        .score(30)
                        .description("用户每小时领券次数超限: " + hourCount)
                        .build());
                log.debug("User {} exceeds hourly coupon limit: {}", userId, hourCount);
            }

            if (dayCount != null && dayCount > maxCouponsPerUserPerDay) {
                result.getRisks().add(RiskItem.builder()
                        .type("USER_FREQUENCY_DAILY")
                        .level("HIGH")
                        .score(25)
                        .description("用户每日领券次数超限: " + dayCount)
                        .build());
                log.debug("User {} exceeds daily coupon limit: {}", userId, dayCount);
            }

        } catch (Exception e) {
            log.error("Failed to check user frequency: {}", userId, e);
        }
    }

    private void checkRequestInterval(String userId, FraudCheckResult result) {
        String lastRequestKey = USER_FREQUENCY_KEY + "last:" + userId;
        try {
            String lastRequestStr = redisTemplate.opsForValue().get(lastRequestKey);
            long now = System.currentTimeMillis();

            if (lastRequestStr != null) {
                long lastRequest = Long.parseLong(lastRequestStr);
                long interval = now - lastRequest;
                if (interval < minIntervalMs) {
                    result.getRisks().add(RiskItem.builder()
                            .type("REQUEST_TOO_FAST")
                            .level("MEDIUM")
                            .score(15)
                            .description("请求间隔过短: " + interval + "ms")
                            .build());
                    log.debug("User {} request interval too short: {}ms", userId, interval);
                }
            }

            redisTemplate.opsForValue().set(lastRequestKey, String.valueOf(now), 5, TimeUnit.MINUTES);

        } catch (Exception e) {
            log.error("Failed to check request interval: {}", userId, e);
        }
    }

    private void checkIpClustering(String clientIp, String userId, FraudCheckResult result) {
        String key = IP_USER_MAPPING_KEY + clientIp;
        try {
            redisTemplate.opsForSet().add(key, userId);
            redisTemplate.expire(key, 24, TimeUnit.HOURS);

            Long userCount = redisTemplate.opsForSet().size(key);
            if (userCount != null && userCount > maxUsersPerIp) {
                result.getRisks().add(RiskItem.builder()
                        .type("IP_CLUSTERING")
                        .level("HIGH")
                        .score(35)
                        .description("IP地址关联过多用户: " + userCount)
                        .build());
                log.warn("IP {} has too many users: {}", clientIp, userCount);

                if (userCount > maxUsersPerIp * 2) {
                    detectBatchAccounts(clientIp, key, "IP");
                }
            }

        } catch (Exception e) {
            log.error("Failed to check IP clustering: {}", clientIp, e);
        }
    }

    private void checkIpFrequency(String clientIp, FraudCheckResult result) {
        String key = IP_FREQUENCY_KEY + LocalDateTime.now().format(HOUR_FORMATTER) + ":" + clientIp;
        try {
            Long count = redisTemplate.opsForValue().increment(key);
            if (count != null && count == 1) {
                redisTemplate.expire(key, 1, TimeUnit.HOURS);
            }

            if (count != null && count > maxUsersPerIp * 10) {
                result.getRisks().add(RiskItem.builder()
                        .type("IP_FREQUENCY")
                        .level("HIGH")
                        .score(25)
                        .description("IP地址请求频率过高: " + count + "/小时")
                        .build());
            }

        } catch (Exception e) {
            log.error("Failed to check IP frequency: {}", clientIp, e);
        }
    }

    private void checkDeviceClustering(String deviceId, String userId, FraudCheckResult result) {
        String key = DEVICE_USER_MAPPING_KEY + deviceId;
        try {
            redisTemplate.opsForSet().add(key, userId);
            redisTemplate.expire(key, 7, TimeUnit.DAYS);

            Long userCount = redisTemplate.opsForSet().size(key);
            if (userCount != null && userCount > maxUsersPerDevice) {
                result.getRisks().add(RiskItem.builder()
                        .type("DEVICE_CLUSTERING")
                        .level("HIGH")
                        .score(40)
                        .description("设备关联过多用户: " + userCount)
                        .build());
                log.warn("Device {} has too many users: {}", deviceId, userCount);

                if (userCount > maxUsersPerDevice * 2) {
                    detectBatchAccounts(deviceId, key, "DEVICE");
                }
            }

        } catch (Exception e) {
            log.error("Failed to check device clustering: {}", deviceId, e);
        }
    }

    private void checkDeviceEmulator(String deviceId, FraudCheckResult result) {
        if (deviceId.length() < 10 || deviceId.matches("^(0+|1+|2+)$")) {
            result.getRisks().add(RiskItem.builder()
                    .type("SUSPICIOUS_DEVICE")
                    .level("HIGH")
                    .score(45)
                    .description("可疑设备ID格式: " + deviceId)
                    .build());
            log.debug("Suspicious device ID format: {}", deviceId);
        }

        if (deviceId.startsWith("emulator-") || deviceId.startsWith("genymotion-")) {
            result.getRisks().add(RiskItem.builder()
                    .type("EMULATOR_DETECTED")
                    .level("HIGH")
                    .score(50)
                    .description("检测到模拟器设备")
                    .build());
        }
    }

    private void checkUserPattern(String userId, FraudCheckResult result) {
        if (userId.length() < 5 || userId.matches("^user[0-9]{1,3}$")) {
            result.getRisks().add(RiskItem.builder()
                    .type("SUSPICIOUS_USER_ID")
                    .level("LOW")
                    .score(10)
                    .description("可疑的用户ID格式")
                    .build());
        }
    }

    private void checkAccountAge(String userId, FraudCheckResult result) {
        String ageKey = "user:create_time:" + userId;
        try {
            String createTimeStr = redisTemplate.opsForValue().get(ageKey);
            if (createTimeStr != null) {
                long createTime = Long.parseLong(createTimeStr);
                long ageHours = (System.currentTimeMillis() - createTime) / (1000 * 3600);
                if (ageHours < 24) {
                    result.getRisks().add(RiskItem.builder()
                            .type("NEW_ACCOUNT")
                            .level("LOW")
                            .score(15)
                            .description("新注册账号: " + ageHours + "小时")
                            .build());
                }
            }
        } catch (Exception e) {
            log.debug("Could not check account age for user: {}", userId);
        }
    }

    private void checkBlacklist(String userId, String clientIp, String deviceId, FraudCheckResult result) {
        try {
            if (Boolean.TRUE.equals(redisTemplate.opsForSet().isMember(BLACKLIST_KEY + "user", userId))) {
                result.getRisks().add(RiskItem.builder()
                        .type("BLACKLISTED_USER")
                        .level("CRITICAL")
                        .score(100)
                        .description("用户在黑名单中")
                        .build());
            }

            if (clientIp != null && Boolean.TRUE.equals(redisTemplate.opsForSet().isMember(BLACKLIST_KEY + "ip", clientIp))) {
                result.getRisks().add(RiskItem.builder()
                        .type("BLACKLISTED_IP")
                        .level("CRITICAL")
                        .score(100)
                        .description("IP地址在黑名单中")
                        .build());
            }

            if (deviceId != null && Boolean.TRUE.equals(redisTemplate.opsForSet().isMember(BLACKLIST_KEY + "device", deviceId))) {
                result.getRisks().add(RiskItem.builder()
                        .type("BLACKLISTED_DEVICE")
                        .level("CRITICAL")
                        .score(100)
                        .description("设备在黑名单中")
                        .build());
            }

        } catch (Exception e) {
            log.error("Failed to check blacklist: {}", userId, e);
        }
    }

    private void detectBatchAccounts(String identifier, String mappingKey, String type) {
        String batchKey = SUSPECT_BATCH_KEY + type + ":" + identifier + ":"
                + LocalDateTime.now().format(HOUR_FORMATTER);
        try {
            Set<Object> users = redisTemplate.opsForSet().members(mappingKey);
            if (users != null && users.size() > maxUsersPerIp * 2) {
                List<String> userList = new ArrayList<>();
                for (Object user : users) {
                    userList.add(user.toString());
                }
                String batchInfo = com.alibaba.fastjson2.JSON.toJSONString(userList);
                redisTemplate.opsForValue().set(batchKey, batchInfo, 7, TimeUnit.DAYS);
                log.warn("Detected potential batch accounts {}: {} has {} users",
                        type, identifier, users.size());
            }
        } catch (Exception e) {
            log.error("Failed to detect batch accounts: {}", identifier, e);
        }
    }

    private void calculateFinalRiskScore(FraudCheckResult result) {
        int totalScore = 0;
        for (RiskItem risk : result.getRisks()) {
            totalScore += risk.getScore();
        }
        result.setRiskScore(Math.min(totalScore, 100));
    }

    private void recordCheckResult(String userId, FraudCheckResult result) {
        String key = RISK_SCORE_KEY + userId;
        try {
            String json = com.alibaba.fastjson2.JSON.toJSONString(result);
            redisTemplate.opsForValue().set(key, json, 24, TimeUnit.HOURS);
        } catch (Exception e) {
            log.error("Failed to record check result: {}", userId, e);
        }
    }

    public void addToBlacklist(String userId, String ip, String deviceId, int hours) {
        try {
            if (userId != null) {
                redisTemplate.opsForSet().add(BLACKLIST_KEY + "user", userId);
                redisTemplate.expire(BLACKLIST_KEY + "user", hours, TimeUnit.HOURS);
                log.info("Added user {} to blacklist for {} hours", userId, hours);
            }
            if (ip != null) {
                redisTemplate.opsForSet().add(BLACKLIST_KEY + "ip", ip);
                redisTemplate.expire(BLACKLIST_KEY + "ip", hours, TimeUnit.HOURS);
                log.info("Added IP {} to blacklist for {} hours", ip, hours);
            }
            if (deviceId != null) {
                redisTemplate.opsForSet().add(BLACKLIST_KEY + "device", deviceId);
                redisTemplate.expire(BLACKLIST_KEY + "device", hours, TimeUnit.HOURS);
                log.info("Added device {} to blacklist for {} hours", deviceId, hours);
            }
        } catch (Exception e) {
            log.error("Failed to add to blacklist", e);
        }
    }

    public void removeFromBlacklist(String userId, String ip, String deviceId) {
        try {
            if (userId != null) {
                redisTemplate.opsForSet().remove(BLACKLIST_KEY + "user", userId);
            }
            if (ip != null) {
                redisTemplate.opsForSet().remove(BLACKLIST_KEY + "ip", ip);
            }
            if (deviceId != null) {
                redisTemplate.opsForSet().remove(BLACKLIST_KEY + "device", deviceId);
            }
        } catch (Exception e) {
            log.error("Failed to remove from blacklist", e);
        }
    }

    public FraudCheckResult getLatestRiskScore(String userId) {
        String key = RISK_SCORE_KEY + userId;
        try {
            String json = redisTemplate.opsForValue().get(key);
            if (json != null) {
                return com.alibaba.fastjson2.JSON.parseObject(json, FraudCheckResult.class);
            }
        } catch (Exception e) {
            log.error("Failed to get risk score: {}", userId, e);
        }
        return null;
    }

    public FraudStatistics getFraudStatistics() {
        FraudStatistics stats = new FraudStatistics();
        try {
            Long blacklistedUsers = redisTemplate.opsForSet().size(BLACKLIST_KEY + "user");
            Long blacklistedIps = redisTemplate.opsForSet().size(BLACKLIST_KEY + "ip");
            Long blacklistedDevices = redisTemplate.opsForSet().size(BLACKLIST_KEY + "device");

            stats.setBlacklistedUsers(blacklistedUsers != null ? blacklistedUsers : 0);
            stats.setBlacklistedIps(blacklistedIps != null ? blacklistedIps : 0);
            stats.setBlacklistedDevices(blacklistedDevices != null ? blacklistedDevices : 0);

            stats.setRiskThreshold(riskThreshold);
            stats.setMaxCouponsPerHour(maxCouponsPerUserPerHour);
            stats.setMaxCouponsPerDay(maxCouponsPerUserPerDay);
            stats.setMaxUsersPerIp(maxUsersPerIp);
            stats.setMaxUsersPerDevice(maxUsersPerDevice);

        } catch (Exception e) {
            log.error("Failed to get fraud statistics", e);
        }
        return stats;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FraudCheckResult implements Serializable {
        private static final long serialVersionUID = 1L;
        private String userId;
        private LocalDateTime checkTime;
        private boolean passed;
        private int riskScore;
        private List<RiskItem> risks;
        private String blockReason;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RiskItem implements Serializable {
        private static final long serialVersionUID = 1L;
        private String type;
        private String level;
        private int score;
        private String description;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FraudStatistics implements Serializable {
        private static final long serialVersionUID = 1L;
        private long blacklistedUsers;
        private long blacklistedIps;
        private long blacklistedDevices;
        private int riskThreshold;
        private int maxCouponsPerHour;
        private int maxCouponsPerDay;
        private int maxUsersPerIp;
        private int maxUsersPerDevice;
    }
}

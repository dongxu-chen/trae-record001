package com.coupon.redis.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.model.UserProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class UserProfileCacheService {

    private static final String KEY_PREFIX = "user:profile:";
    private static final String COUPON_HISTORY_PREFIX = "user:coupon_history:";
    private static final int HISTORY_WINDOW_DAYS = 7;

    private final StringRedisTemplate redisTemplate;

    @Value("${coupon.cache.user-profile-ttl:3600}")
    private long ttlSeconds;

    public UserProfileCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void saveUserProfile(UserProfile profile) {
        String key = getKey(profile.getUserId());
        try {
            profile.setUpdateTime(LocalDateTime.now());
            String json = JSON.toJSONString(profile);
            redisTemplate.opsForValue().set(key, json, ttlSeconds, TimeUnit.SECONDS);
            log.debug("Cached user profile for user: {}", profile.getUserId());
        } catch (Exception e) {
            log.error("Failed to cache user profile for user: {}", profile.getUserId(), e);
        }
    }

    public UserProfile getUserProfile(String userId) {
        String key = getKey(userId);
        try {
            String json = redisTemplate.opsForValue().get(key);
            if (json != null) {
                UserProfile profile = JSON.parseObject(json, UserProfile.class);
                log.debug("Retrieved cached user profile for user: {}", userId);
                return profile;
            }
        } catch (Exception e) {
            log.error("Failed to retrieve user profile for user: {}", userId, e);
        }
        return null;
    }

    public UserProfile getOrCreateDefault(String userId) {
        UserProfile profile = getUserProfile(userId);
        if (profile == null) {
            profile = createDefaultProfile(userId);
            saveUserProfile(profile);
        }
        return profile;
    }

    public void updateUserActivity(String userId) {
        UserProfile profile = getOrCreateDefault(userId);
        profile.setLastActiveTime(LocalDateTime.now());
        profile.setActivityScore(Math.min(100, profile.getActivityScore() + 1));
        profile.setDaysSinceLastOrder(0);
        saveUserProfile(profile);
    }

    public void updateUserAfterOrder(String userId, double orderAmount) {
        UserProfile profile = getOrCreateDefault(userId);
        profile.setOrderCount30d(profile.getOrderCount30d() + 1);
        profile.setTotalSpend(profile.getTotalSpend() + orderAmount);
        profile.setDaysSinceLastOrder(0);

        int orderCount = profile.getOrderCount30d();
        if (orderCount > 0) {
            profile.setAvgOrderValue(profile.getTotalSpend() / orderCount);
        }
        profile.setConsumptionFrequency(Math.min(30, orderCount / 30.0 * 30));

        saveUserProfile(profile);
    }

    public void updateCouponUsage(String userId, boolean used) {
        UserProfile profile = getOrCreateDefault(userId);
        double currentRate = profile.getCouponUsageRate();
        double newRate = used ? (currentRate + 0.1) : (currentRate - 0.05);
        profile.setCouponUsageRate(Math.max(0, Math.min(1, newRate)));
        saveUserProfile(profile);
    }

    public boolean exists(String userId) {
        String key = getKey(userId);
        try {
            return Boolean.TRUE.equals(redisTemplate.hasKey(key));
        } catch (Exception e) {
            log.error("Failed to check user profile existence: {}", userId, e);
            return false;
        }
    }

    public void deleteUserProfile(String userId) {
        String key = getKey(userId);
        try {
            redisTemplate.delete(key);
            log.debug("Deleted cached user profile for user: {}", userId);
        } catch (Exception e) {
            log.error("Failed to delete user profile: {}", userId, e);
        }
    }

    public void recordCouponHistory(String userId, int couponType, int denomination) {
        String key = getCouponHistoryKey(userId);
        long timestamp = System.currentTimeMillis();
        String member = couponType + ":" + denomination + ":" + timestamp;

        try {
            ZSetOperations<String, String> zSetOps = redisTemplate.opsForZSet();
            zSetOps.add(key, member, timestamp);

            long cutoff = timestamp - HISTORY_WINDOW_DAYS * 24 * 3600 * 1000L;
            zSetOps.removeRangeByScore(key, 0, cutoff);
            redisTemplate.expire(key, HISTORY_WINDOW_DAYS, TimeUnit.DAYS);

            UserProfile profile = getOrCreateDefault(userId);
            profile.recordCouponIssue(couponType, denomination);
            refreshCouponHistoryFromRedis(profile, userId);
            saveUserProfile(profile);

            log.debug("Recorded coupon history for user {}: type={}, denomination={}",
                    userId, couponType, denomination);
        } catch (Exception e) {
            log.error("Failed to record coupon history for user: {}", userId, e);
        }
    }

    public void refreshCouponHistoryFromRedis(UserProfile profile, String userId) {
        String key = getCouponHistoryKey(userId);
        try {
            ZSetOperations<String, String> zSetOps = redisTemplate.opsForZSet();
            long cutoff = System.currentTimeMillis() - HISTORY_WINDOW_DAYS * 24 * 3600 * 1000L;

            Set<String> history = zSetOps.rangeByScore(key, cutoff, Double.MAX_VALUE);
            if (history != null && !history.isEmpty()) {
                profile.initCouponHistoryArrays();
                profile.setCouponIssueCount7d(history.size());

                int daysSinceLast = Integer.MAX_VALUE;
                for (String entry : history) {
                    String[] parts = entry.split(":");
                    if (parts.length >= 3) {
                        int type = Integer.parseInt(parts[0]);
                        int denom = Integer.parseInt(parts[1]);
                        long ts = Long.parseLong(parts[2]);

                        int typeIdx = Math.max(0, Math.min(4, type - 1));
                        profile.getCouponTypeDistribution7d()[typeIdx]++;

                        int denomIdx = Math.min(3, denom / 15);
                        profile.getCouponDenominationDistribution7d()[denomIdx]++;

                        long daysAgo = (System.currentTimeMillis() - ts) / (24 * 3600 * 1000L);
                        if (daysAgo < daysSinceLast) {
                            daysSinceLast = (int) daysAgo;
                        }

                        if (daysSinceLast == 0) {
                            profile.setLastCouponType(type);
                            profile.setLastCouponDenomination(denom);
                        }
                    }
                }

                if (daysSinceLast == Integer.MAX_VALUE) {
                    profile.setDaysSinceLastCoupon(0);
                } else {
                    profile.setDaysSinceLastCoupon(daysSinceLast);
                }
            } else {
                profile.setDaysSinceLastCoupon(30);
            }
        } catch (Exception e) {
            log.error("Failed to refresh coupon history from Redis for user: {}", userId, e);
        }
    }

    public boolean hasRecentSimilarCoupon(String userId, int couponType, int denomination) {
        UserProfile profile = getOrCreateDefault(userId);
        refreshCouponHistoryFromRedis(profile, userId);
        return profile.hasRecentSimilarCoupon(couponType, denomination);
    }

    public void incrementDaysSinceLastCoupon(String userId) {
        UserProfile profile = getUserProfile(userId);
        if (profile != null) {
            int currentDays = profile.getDaysSinceLastCoupon();
            if (currentDays < 30) {
                profile.setDaysSinceLastCoupon(currentDays + 1);
                saveUserProfile(profile);
            }
        }
    }

    private UserProfile createDefaultProfile(String userId) {
        UserProfile profile = UserProfile.builder()
                .userId(userId)
                .consumptionFrequency(0)
                .avgOrderValue(0)
                .activityScore(50)
                .totalSpend(0)
                .orderCount30d(0)
                .daysSinceLastOrder(0)
                .couponUsageRate(0.5)
                .avgDiscountSensitivity(0.5)
                .isNewUser(true)
                .userLevel(1)
                .registerTime(LocalDateTime.now())
                .lastActiveTime(LocalDateTime.now())
                .updateTime(LocalDateTime.now())
                .couponIssueCount7d(0)
                .couponUseCount7d(0)
                .daysSinceLastCoupon(30)
                .build();
        profile.initCouponHistoryArrays();
        return profile;
    }

    private String getKey(String userId) {
        return KEY_PREFIX + userId;
    }

    private String getCouponHistoryKey(String userId) {
        return COUPON_HISTORY_PREFIX + userId;
    }
}

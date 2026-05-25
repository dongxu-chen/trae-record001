package com.coupon.personalization.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.model.UserProfile;
import com.coupon.model.enums.CouponType;
import com.coupon.model.enums.SceneType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class CouponPersonalizationService {

    private static final String PRICE_SENSITIVITY_KEY = "personalization:price_sensitivity:";
    private static final String COUPON_TEMPLATE_KEY = "personalization:template:";
    private static final String USER_PREFERENCE_KEY = "personalization:preference:";
    private static final String HISTORY_CONVERSION_KEY = "personalization:conversion:";

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final StringRedisTemplate redisTemplate;

    @Value("${coupon.personalization.enable:true}")
    private boolean enablePersonalization;

    @Value("${coupon.personalization.default-discount-rate:0.1}")
    private double defaultDiscountRate;

    @Value("${coupon.personalization.max-adjustment-percent:20}")
    private int maxAdjustmentPercent;

    private final Map<Integer, String> couponThemes = new ConcurrentHashMap<>();

    public CouponPersonalizationService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
        initThemes();
    }

    private void initThemes() {
        couponThemes.put(1, "生日专享");
        couponThemes.put(2, "会员专享");
        couponThemes.put(3, "节日特惠");
        couponThemes.put(4, "新人礼包");
        couponThemes.put(5, "复购奖励");
        couponThemes.put(6, "限时抢购");
        couponThemes.put(7, "品牌专属");
        couponThemes.put(8, "品类券");
    }

    public PersonalizedCouponRecommendation personalizeCoupon(String userId, UserProfile profile,
                                                               SceneType sceneType,
                                                               BigDecimal baseDenomination,
                                                               CouponType baseType) {
        PersonalizedCouponRecommendation recommendation = PersonalizedCouponRecommendation.builder()
                .userId(userId)
                .sceneType(sceneType)
                .originalDenomination(baseDenomination)
                .originalCouponType(baseType)
                .adjustedDenomination(baseDenomination)
                .adjustedCouponType(baseType)
                .build();

        if (!enablePersonalization || profile == null) {
            return recommendation;
        }

        try {
            PriceSensitivity sensitivity = calculatePriceSensitivity(userId, profile);
            recommendation.setPriceSensitivity(sensitivity);

            BigDecimal adjustedDenomination = adjustDenominationBySensitivity(
                    baseDenomination, sensitivity.getSensitivityScore());
            recommendation.setAdjustedDenomination(adjustedDenomination);

            CouponType adjustedType = selectOptimalCouponType(profile, baseType, sensitivity);
            recommendation.setAdjustedCouponType(adjustedType);

            String theme = selectPersonalizedTheme(profile, sceneType);
            recommendation.setCouponTheme(theme);

            String personalizedMessage = generatePersonalizedMessage(profile, recommendation);
            recommendation.setPersonalizedMessage(personalizedMessage);

            BigDecimal minOrderAmount = calculateMinOrderAmount(profile, adjustedDenomination);
            recommendation.setMinOrderAmount(minOrderAmount);

            Map<String, String> displayConfig = generateDisplayConfig(profile, recommendation);
            recommendation.setDisplayConfig(displayConfig);

            updateUserPreference(userId, recommendation);

            log.debug("Personalized coupon for user {}: original={}, adjusted={}, sensitivity={}",
                    userId, baseDenomination, adjustedDenomination, sensitivity.getSensitivityLevel());

        } catch (Exception e) {
            log.error("Failed to personalize coupon for user: {}", userId, e);
        }

        return recommendation;
    }

    public PriceSensitivity calculatePriceSensitivity(String userId, UserProfile profile) {
        String cacheKey = PRICE_SENSITIVITY_KEY + userId;
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                PriceSensitivity sensitivity = JSON.parseObject(cached, PriceSensitivity.class);
                if (sensitivity != null &&
                        System.currentTimeMillis() - sensitivity.getCalculateTime() < 24 * 3600 * 1000) {
                    return sensitivity;
                }
            }
        } catch (Exception e) {
            log.debug("No cached sensitivity for user: {}", userId);
        }

        PriceSensitivity sensitivity = new PriceSensitivity();
        sensitivity.setUserId(userId);
        sensitivity.setCalculateTime(System.currentTimeMillis());

        try {
            double frequencyScore = calculateFrequencyScore(profile);
            double monetaryScore = calculateMonetaryScore(profile);
            double historicalScore = calculateHistoricalConversionScore(userId);
            double categoryPreferenceScore = calculateCategoryPreferenceScore(profile);
            double activityScore = profile.getActivityScore() / 100.0;

            double rawScore = (frequencyScore * 0.25
                    + monetaryScore * 0.30
                    + historicalScore * 0.25
                    + categoryPreferenceScore * 0.10
                    + activityScore * 0.10);

            int sensitivityScore = (int) Math.round(rawScore * 100);
            sensitivityScore = Math.max(0, Math.min(100, sensitivityScore));

            sensitivity.setSensitivityScore(sensitivityScore);
            sensitivity.setSensitivityLevel(determineSensitivityLevel(sensitivityScore));
            sensitivity.setFrequencyScore(frequencyScore);
            sensitivity.setMonetaryScore(monetaryScore);
            sensitivity.setHistoricalScore(historicalScore);
            sensitivity.setCategoryPreferenceScore(categoryPreferenceScore);
            sensitivity.setActivityScore(activityScore);

            String json = JSON.toJSONString(sensitivity);
            redisTemplate.opsForValue().set(cacheKey, json, 24, TimeUnit.HOURS);

        } catch (Exception e) {
            log.error("Failed to calculate price sensitivity: {}", userId, e);
            sensitivity.setSensitivityScore(50);
            sensitivity.setSensitivityLevel("MEDIUM");
        }

        return sensitivity;
    }

    private double calculateFrequencyScore(UserProfile profile) {
        double frequency = profile.getConsumptionFrequency();
        if (frequency <= 1) return 0.8;
        if (frequency <= 3) return 0.6;
        if (frequency <= 6) return 0.4;
        if (frequency <= 10) return 0.3;
        return 0.2;
    }

    private double calculateMonetaryScore(UserProfile profile) {
        double avgOrder = profile.getAvgOrderValue();
        if (avgOrder <= 50) return 0.9;
        if (avgOrder <= 100) return 0.7;
        if (avgOrder <= 200) return 0.5;
        if (avgOrder <= 500) return 0.3;
        return 0.15;
    }

    private double calculateHistoricalConversionScore(String userId) {
        String key = HISTORY_CONVERSION_KEY + userId;
        try {
            Map<Object, Object> data = redisTemplate.opsForHash().entries(key);
            if (data.isEmpty()) {
                return 0.5;
            }

            String totalStr = (String) data.getOrDefault("total", "0");
            String usedStr = (String) data.getOrDefault("used", "0");

            int total = Integer.parseInt(totalStr);
            int used = Integer.parseInt(usedStr);

            if (total == 0) return 0.5;

            double conversionRate = (double) used / total;

            if (conversionRate <= 0.2) return 0.8;
            if (conversionRate <= 0.4) return 0.6;
            if (conversionRate <= 0.6) return 0.5;
            if (conversionRate <= 0.8) return 0.4;
            return 0.25;

        } catch (Exception e) {
            log.debug("No conversion history for user: {}", userId);
            return 0.5;
        }
    }

    private double calculateCategoryPreferenceScore(UserProfile profile) {
        if (profile.getPreferredCategories() == null || profile.getPreferredCategories().isEmpty()) {
            return 0.5;
        }
        int categories = profile.getPreferredCategories().size();
        if (categories >= 5) return 0.3;
        if (categories >= 3) return 0.5;
        return 0.7;
    }

    private String determineSensitivityLevel(int score) {
        if (score >= 70) return "HIGH";
        if (score >= 40) return "MEDIUM";
        return "LOW";
    }

    private BigDecimal adjustDenominationBySensitivity(BigDecimal baseDenomination, int sensitivityScore) {
        double adjustmentFactor;

        if (sensitivityScore >= 70) {
            adjustmentFactor = 1 + (maxAdjustmentPercent / 100.0);
        } else if (sensitivityScore >= 40) {
            adjustmentFactor = 1.0;
        } else if (sensitivityScore >= 20) {
            adjustmentFactor = 1 - (maxAdjustmentPercent / 200.0);
        } else {
            adjustmentFactor = 1 - (maxAdjustmentPercent / 100.0);
        }

        BigDecimal adjusted = baseDenomination.multiply(BigDecimal.valueOf(adjustmentFactor))
                .setScale(0, RoundingMode.HALF_UP);

        BigDecimal maxDenomination = baseDenomination.multiply(BigDecimal.valueOf(1.5));
        BigDecimal minDenomination = baseDenomination.multiply(BigDecimal.valueOf(0.5));

        if (adjusted.compareTo(maxDenomination) > 0) {
            adjusted = maxDenomination.setScale(0, RoundingMode.HALF_UP);
        }
        if (adjusted.compareTo(minDenomination) < 0) {
            adjusted = minDenomination.setScale(0, RoundingMode.HALF_UP);
        }

        return adjusted;
    }

    private CouponType selectOptimalCouponType(UserProfile profile, CouponType baseType,
                                               PriceSensitivity sensitivity) {
        String level = sensitivity.getSensitivityLevel();

        if ("HIGH".equals(level)) {
            return CouponType.FULL_DISCOUNT;
        } else if ("MEDIUM".equals(level)) {
            if (baseType == CouponType.PERCENTAGE_DISCOUNT) {
                return CouponType.PERCENTAGE_DISCOUNT;
            }
            return CouponType.FULL_DISCOUNT;
        } else {
            double avgOrder = profile.getAvgOrderValue();
            if (avgOrder > 200) {
                return CouponType.PERCENTAGE_DISCOUNT;
            }
            if (profile.getPreferredCategories() != null && profile.getPreferredCategories().size() > 0) {
                return CouponType.CATEGORY_SPECIFIC;
            }
            return CouponType.FULL_DISCOUNT;
        }
    }

    private String selectPersonalizedTheme(UserProfile profile, SceneType sceneType) {
        if (profile.getUserLevel() >= 3) {
            return "会员专享";
        }

        if (profile.getBirthday() != null && isNearBirthday(profile.getBirthday())) {
            return "生日专享";
        }

        if (sceneType == SceneType.NEW_USER) {
            return "新人礼包";
        }
        if (sceneType == SceneType.REPURCHASE) {
            return "复购奖励";
        }
        if (sceneType == SceneType.WAKE_UP) {
            return "限时抢购";
        }

        if (profile.getPreferredCategories() != null && profile.getPreferredCategories().size() == 1) {
            return "品类券";
        }

        return "品牌专属";
    }

    private boolean isNearBirthday(String birthday) {
        try {
            LocalDateTime birthDate = LocalDateTime.parse(birthday,
                    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            LocalDateTime now = LocalDateTime.now();

            int birthDayOfYear = birthDate.getDayOfYear();
            int nowDayOfYear = now.getDayOfYear();

            int diff = Math.abs(birthDayOfYear - nowDayOfYear);
            return diff <= 7 || diff >= 358;

        } catch (Exception e) {
            return false;
        }
    }

    private String generatePersonalizedMessage(UserProfile profile,
                                               PersonalizedCouponRecommendation recommendation) {
        String sensitivityLevel = recommendation.getPriceSensitivity().getSensitivityLevel();
        BigDecimal adjustedAmount = recommendation.getAdjustedDenomination();
        String theme = recommendation.getCouponTheme();

        Map<String, String> messages = new HashMap<>();
        messages.put("HIGH", "限时特惠！" + adjustedAmount + "元" + theme + "券，手慢无！");
        messages.put("MEDIUM", "专属福利！为您准备了" + adjustedAmount + "元优惠券，立即使用吧~");
        messages.put("LOW", "尊贵会员，" + adjustedAmount + "元" + theme + "券已到账，尊享优惠！");

        return messages.getOrDefault(sensitivityLevel,
                adjustedAmount + "元优惠券已为您准备好！");
    }

    private BigDecimal calculateMinOrderAmount(UserProfile profile, BigDecimal denomination) {
        double avgOrder = profile.getAvgOrderValue();
        BigDecimal minOrder;

        if (avgOrder > 0) {
            minOrder = denomination.multiply(BigDecimal.valueOf(2))
                    .setScale(0, RoundingMode.HALF_UP);

            BigDecimal avgOrderBD = BigDecimal.valueOf(avgOrder);
            if (minOrder.compareTo(avgOrderBD.multiply(BigDecimal.valueOf(0.8))) < 0) {
                minOrder = avgOrderBD.multiply(BigDecimal.valueOf(0.8))
                        .setScale(0, RoundingMode.HALF_UP);
            }
        } else {
            minOrder = denomination.multiply(BigDecimal.valueOf(3))
                    .setScale(0, RoundingMode.HALF_UP);
        }

        if (minOrder.compareTo(BigDecimal.TEN) < 0) {
            minOrder = BigDecimal.TEN;
        }

        return minOrder;
    }

    private Map<String, String> generateDisplayConfig(UserProfile profile,
                                                      PersonalizedCouponRecommendation recommendation) {
        Map<String, String> config = new HashMap<>();
        String level = recommendation.getPriceSensitivity().getSensitivityLevel();

        Map<String, String> colors = new HashMap<>();
        colors.put("HIGH", "#FF4444");
        colors.put("MEDIUM", "#FF8800");
        colors.put("LOW", "#3366FF");

        Map<String, String> fonts = new HashMap<>();
        fonts.put("HIGH", "bold_large");
        fonts.put("MEDIUM", "normal");
        fonts.put("LOW", "elegant");

        config.put("primaryColor", colors.getOrDefault(level, "#FF8800"));
        config.put("fontStyle", fonts.getOrDefault(level, "normal"));
        config.put("showCountdown", "HIGH".equals(level) ? "true" : "false");
        config.put("animationStyle", "HIGH".equals(level) ? "pulse" : "fade");
        config.put("position", profile.getActivityScore() > 70 ? "top" : "center");

        return config;
    }

    private void updateUserPreference(String userId, PersonalizedCouponRecommendation recommendation) {
        String key = USER_PREFERENCE_KEY + userId;
        try {
            String json = JSON.toJSONString(recommendation);
            redisTemplate.opsForValue().set(key, json, 7, TimeUnit.DAYS);
        } catch (Exception e) {
            log.debug("Failed to update user preference: {}", userId);
        }
    }

    public void recordCouponConversion(String userId, boolean used) {
        String key = HISTORY_CONVERSION_KEY + userId;
        try {
            redisTemplate.opsForHash().increment(key, "total", 1);
            if (used) {
                redisTemplate.opsForHash().increment(key, "used", 1);
            }
            redisTemplate.expire(key, 90, TimeUnit.DAYS);

            redisTemplate.delete(PRICE_SENSITIVITY_KEY + userId);

        } catch (Exception e) {
            log.debug("Failed to record conversion: {}", userId);
        }
    }

    public PersonalizedCouponRecommendation getLatestRecommendation(String userId) {
        String key = USER_PREFERENCE_KEY + userId;
        try {
            String json = redisTemplate.opsForValue().get(key);
            if (json != null) {
                return JSON.parseObject(json, PersonalizedCouponRecommendation.class);
            }
        } catch (Exception e) {
            log.error("Failed to get latest recommendation: {}", userId, e);
        }
        return null;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PriceSensitivity implements Serializable {
        private static final long serialVersionUID = 1L;
        private String userId;
        private int sensitivityScore;
        private String sensitivityLevel;
        private double frequencyScore;
        private double monetaryScore;
        private double historicalScore;
        private double categoryPreferenceScore;
        private double activityScore;
        private long calculateTime;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PersonalizedCouponRecommendation implements Serializable {
        private static final long serialVersionUID = 1L;
        private String userId;
        private SceneType sceneType;
        private BigDecimal originalDenomination;
        private CouponType originalCouponType;
        private BigDecimal adjustedDenomination;
        private CouponType adjustedCouponType;
        private String couponTheme;
        private String personalizedMessage;
        private BigDecimal minOrderAmount;
        private Map<String, String> displayConfig;
        private PriceSensitivity priceSensitivity;
    }
}

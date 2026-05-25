package com.coupon.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.abtest.service.ABTestTrackingService;
import com.coupon.abtest.service.ExperimentService;
import com.coupon.clickhouse.repository.CouponDistributionRepository;
import com.coupon.clickhouse.service.EffectEvaluationService;
import com.coupon.model.CouponDistribution;
import com.coupon.model.ExperimentConfig;
import com.coupon.model.UserProfile;
import com.coupon.model.enums.CouponStatus;
import com.coupon.model.enums.CouponType;
import com.coupon.model.enums.SceneType;
import com.coupon.notification.service.CouponNotificationService;
import com.coupon.personalization.service.CouponPersonalizationService;
import com.coupon.redis.service.CouponStockService;
import com.coupon.redis.service.UserProfileCacheService;
import com.coupon.rl.agent.DQNAgent;
import com.coupon.rl.model.CouponAction;
import com.coupon.security.service.CouponAntiFraudService;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class CouponDistributionService {

    private final DQNAgent dqnAgent;
    private final UserProfileCacheService userProfileCacheService;
    private final CouponStockService couponStockService;
    private final ExperimentService experimentService;
    private final ABTestTrackingService trackingService;
    private final CouponDistributionRepository distributionRepository;
    private final EffectEvaluationService effectEvaluationService;
    private final CouponAntiFraudService antiFraudService;
    private final CouponPersonalizationService personalizationService;
    private final CouponNotificationService notificationService;

    @Value("${coupon.budget.max-denomination:100}")
    private int maxDenomination;

    @Value("${coupon.antifraud.enable:true}")
    private boolean enableAntiFraud;

    @Value("${coupon.personalization.enable:true}")
    private boolean enablePersonalization;

    private final Map<String, CouponDistribution> pendingDistributions = new ConcurrentHashMap<>();

    public CouponDistributionService(DQNAgent dqnAgent,
                                     UserProfileCacheService userProfileCacheService,
                                     CouponStockService couponStockService,
                                     ExperimentService experimentService,
                                     ABTestTrackingService trackingService,
                                     CouponDistributionRepository distributionRepository,
                                     EffectEvaluationService effectEvaluationService,
                                     CouponAntiFraudService antiFraudService,
                                     CouponPersonalizationService personalizationService,
                                     CouponNotificationService notificationService) {
        this.dqnAgent = dqnAgent;
        this.userProfileCacheService = userProfileCacheService;
        this.couponStockService = couponStockService;
        this.experimentService = experimentService;
        this.trackingService = trackingService;
        this.distributionRepository = distributionRepository;
        this.effectEvaluationService = effectEvaluationService;
        this.antiFraudService = antiFraudService;
        this.personalizationService = personalizationService;
        this.notificationService = notificationService;
    }

    public CouponDecisionResult decideAndIssueCoupon(String userId, SceneType sceneType) {
        return decideAndIssueCoupon(userId, sceneType, null, null);
    }

    public CouponDecisionResult decideAndIssueCoupon(String userId, SceneType sceneType,
                                                     String clientIp, String deviceId) {
        log.info("Processing coupon issue request: userId={}, scene={}, ip={}, device={}",
                userId, sceneType.getDesc(), clientIp, deviceId);

        UserProfile profile = userProfileCacheService.getOrCreateDefault(userId);

        userProfileCacheService.updateUserActivity(userId);
        userProfileCacheService.refreshCouponHistoryFromRedis(profile, userId);

        if (enableAntiFraud) {
            CouponAntiFraudService.FraudCheckResult fraudResult = antiFraudService
                    .performFraudCheck(userId, clientIp, deviceId);
            if (!fraudResult.isPassed()) {
                log.warn("Fraud check failed for user {}: reason={}, riskScore={}",
                        userId, fraudResult.getBlockReason(), fraudResult.getRiskScore());
                return CouponDecisionResult.builder()
                        .userId(userId)
                        .sceneType(sceneType)
                        .success(false)
                        .blockReason(fraudResult.getBlockReason())
                        .riskScore(fraudResult.getRiskScore())
                        .build();
            }
        }

        updateSceneTag(profile, sceneType);

        ExperimentConfig experiment = experimentService.getExperimentByScene(sceneType);
        ExperimentConfig.ExperimentGroup group = experimentService
                .getExperimentGroup(userId, profile, sceneType);

        if (group == null) {
            log.warn("No experiment group found for user {} in scene {}", userId, sceneType);
            return null;
        }

        trackingService.trackExposure(userId, experiment.getExperimentId(), group.getGroupId(), sceneType.name());

        if (!checkBudgetAndLimits(userId)) {
            log.warn("Budget or limit exceeded for user {}", userId);
            return null;
        }

        CouponAction action;
        boolean isRlEnabled = Boolean.TRUE.equals(group.getIsRlEnabled());

        if (isRlEnabled) {
            action = dqnAgent.selectAction(profile);
            log.info("RL action selected for user {}: actionIndex={}, type={}, denomination={}",
                    userId, action.getActionIndex(), action.getCouponType(), action.getDenomination());
        } else {
            action = CouponAction.builder()
                    .actionIndex(-1)
                    .couponType(CouponType.fromCode(group.getFixedCouponType() != null ? group.getFixedCouponType() : 1))
                    .denomination(group.getFixedDenomination() != null ? group.getFixedDenomination() : new BigDecimal("10"))
                    .minOrderAmount(group.getMinOrderAmount() != null ? group.getMinOrderAmount() : new BigDecimal("30"))
                    .validDays(7)
                    .build();
            log.info("Control group action for user {}: type={}, denomination={}",
                    userId, action.getCouponType(), action.getDenomination());
        }

        if (enablePersonalization) {
            CouponPersonalizationService.PersonalizedCouponRecommendation recommendation =
                    personalizationService.personalizeCoupon(
                            userId, profile, sceneType, action.getDenomination(), action.getCouponType());

            action.setDenomination(recommendation.getAdjustedDenomination());
            action.setCouponType(recommendation.getAdjustedCouponType());
            action.setMinOrderAmount(recommendation.getMinOrderAmount());

            log.info("Personalized coupon for user {}: adjusted={} -> {}, sensitivity={}",
                    userId, recommendation.getOriginalDenomination(),
                    recommendation.getAdjustedDenomination(),
                    recommendation.getPriceSensitivity().getSensitivityLevel());
        }

        if (action.getDenomination().compareTo(BigDecimal.valueOf(maxDenomination)) > 0) {
            action.setDenomination(BigDecimal.valueOf(maxDenomination));
        }

        boolean isPromotion = couponStockService.isPromotionActive();
        if (!couponStockService.checkAndConsumeBudget(action.getDenomination().doubleValue(), isPromotion)) {
            log.warn("Budget exceeded for denomination: {}, promotion={}", action.getDenomination(), isPromotion);
            return null;
        }

        String couponId = generateCouponId(sceneType, action);

        if (!couponStockService.deductStock(couponId, 1)) {
            couponStockService.initStock(couponId, 10000);
            couponStockService.deductStock(couponId, 1);
        }

        String distributionId = UUID.randomUUID().toString();
        String couponCode = generateCouponCode();

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime expireTime = now.plusDays(action.getValidDays());

        double[] stateVector = profile.toStateVector();
        String stateVectorJson = JSON.toJSONString(stateVector);

        CouponDistribution distribution = CouponDistribution.builder()
                .distributionId(distributionId)
                .userId(userId)
                .couponId(couponId)
                .couponCode(couponCode)
                .denomination(action.getDenomination())
                .couponType(action.getCouponType().getCode())
                .sceneCode(sceneType.getCode())
                .minOrderAmount(action.getMinOrderAmount())
                .status(CouponStatus.ISSUED)
                .experimentId(experiment.getExperimentId())
                .groupId(group.getGroupId())
                .issueTime(now)
                .expireTime(expireTime)
                .rlActionIndex(isRlEnabled ? action.getActionIndex() : null)
                .stateVector(stateVectorJson)
                .createTime(now)
                .updateTime(now)
                .build();

        distributionRepository.save(distribution);
        pendingDistributions.put(distributionId, distribution);

        userProfileCacheService.recordCouponHistory(userId, action.getCouponType().getCode(),
                action.getDenomination().intValue());

        if (isRlEnabled) {
            trackingService.trackCouponIssue(userId, experiment.getExperimentId(),
                    group.getGroupId(), couponId, sceneType.name(), action.getActionIndex());
        }

        CouponDecisionResult result = CouponDecisionResult.builder()
                .distributionId(distributionId)
                .userId(userId)
                .couponId(couponId)
                .couponCode(couponCode)
                .couponType(action.getCouponType())
                .denomination(action.getDenomination())
                .minOrderAmount(action.getMinOrderAmount())
                .sceneType(sceneType)
                .experimentId(experiment.getExperimentId())
                .groupId(group.getGroupId())
                .isRlEnabled(isRlEnabled)
                .rlActionIndex(isRlEnabled ? action.getActionIndex() : null)
                .issueTime(now)
                .expireTime(expireTime)
                .success(true)
                .build();

        if (enablePersonalization) {
            CouponPersonalizationService.PersonalizedCouponRecommendation recommendation =
                    personalizationService.getLatestRecommendation(userId);
            if (recommendation != null) {
                result.setCouponTheme(recommendation.getCouponTheme());
                result.setPersonalizedMessage(recommendation.getPersonalizedMessage());
                result.setDisplayConfig(recommendation.getDisplayConfig());
                result.setPriceSensitivityScore(recommendation.getPriceSensitivity().getSensitivityScore());
            }
        }

        return result;
    }

    public boolean useCoupon(String distributionId, String orderId, BigDecimal orderAmount) {
        log.info("Processing coupon use: distributionId={}, orderId={}, orderAmount={}",
                distributionId, orderId, orderAmount);

        CouponDistribution distribution = pendingDistributions.get(distributionId);
        if (distribution == null) {
            distribution = distributionRepository.findByUserId(distributionId).stream()
                    .findFirst()
                    .orElse(null);
        }

        if (distribution == null) {
            log.warn("Distribution not found: {}", distributionId);
            return false;
        }

        if (distribution.getStatus() != CouponStatus.ISSUED) {
            log.warn("Coupon not in ISSUED status: {}", distribution.getStatus());
            return false;
        }

        if (distribution.getExpireTime().isBefore(LocalDateTime.now())) {
            log.warn("Coupon expired: {}", distributionId);
            distribution.setStatus(CouponStatus.EXPIRED);
            distributionRepository.updateStatus(distribution);
            return false;
        }

        if (orderAmount.compareTo(distribution.getMinOrderAmount()) < 0) {
            log.warn("Order amount {} below minimum {}", orderAmount, distribution.getMinOrderAmount());
            return false;
        }

        BigDecimal discountAmount = calculateDiscount(distribution, orderAmount);

        distribution.setStatus(CouponStatus.USED);
        distribution.setUseTime(LocalDateTime.now());
        distribution.setOrderId(orderId);
        distribution.setOrderAmount(orderAmount);
        distribution.setDiscountAmount(discountAmount);

        UserProfile currentProfile = userProfileCacheService.getOrCreateDefault(distribution.getUserId());

        dqnAgent.storeExperienceFromDistribution(distribution, currentProfile, null);

        distributionRepository.updateStatus(distribution);

        userProfileCacheService.updateUserAfterOrder(distribution.getUserId(), orderAmount.doubleValue());
        userProfileCacheService.updateCouponUsage(distribution.getUserId(), true);

        trackingService.trackCouponUse(
                distribution.getUserId(),
                distribution.getExperimentId(),
                distribution.getGroupId(),
                distribution.getCouponId(),
                orderId,
                orderAmount.doubleValue(),
                discountAmount.doubleValue()
        );

        pendingDistributions.remove(distributionId);

        log.info("Coupon used successfully: distributionId={}, discount={}", distributionId, discountAmount);
        return true;
    }

    public void expireCoupon(String distributionId) {
        CouponDistribution distribution = pendingDistributions.get(distributionId);
        if (distribution == null) {
            return;
        }

        if (distribution.getStatus() == CouponStatus.ISSUED) {
            distribution.setStatus(CouponStatus.EXPIRED);

            UserProfile currentProfile = userProfileCacheService.getOrCreateDefault(distribution.getUserId());
            dqnAgent.storeExperienceFromDistribution(distribution, currentProfile, null);

            distributionRepository.updateStatus(distribution);

            couponStockService.releaseDailyBudget(distribution.getDenomination().doubleValue());
            userProfileCacheService.updateCouponUsage(distribution.getUserId(), false);

            log.info("Coupon expired: distributionId={}", distributionId);
        }

        pendingDistributions.remove(distributionId);
    }

    private BigDecimal calculateDiscount(CouponDistribution distribution, BigDecimal orderAmount) {
        CouponType type = CouponType.fromCode(distribution.getCouponType());
        BigDecimal denomination = distribution.getDenomination();

        return switch (type) {
            case FULL_DISCOUNT, NEW_USER_ONLY, CATEGORY_SPECIFIC, FREE_SHIPPING -> denomination;
            case PERCENTAGE_DISCOUNT -> {
                BigDecimal discountRate = new BigDecimal("0.9");
                BigDecimal discount = orderAmount.multiply(BigDecimal.ONE.subtract(discountRate));
                yield discount.compareTo(denomination) > 0 ? denomination : discount;
            }
        };
    }

    private boolean checkBudgetAndLimits(String userId) {
        if (!couponStockService.checkDailyCouponLimit()) {
            return false;
        }

        return true;
    }

    private void updateSceneTag(UserProfile profile, SceneType sceneType) {
        switch (sceneType) {
            case NEW_USER -> profile.setNewUser(true);
            case REPURCHASE -> profile.setNewUser(false);
            case WAKE_UP -> {
                profile.setNewUser(false);
                profile.setActivityScore(Math.max(10, profile.getActivityScore() - 5));
            }
        }
    }

    private String generateCouponId(SceneType sceneType, CouponAction action) {
        return String.format("CPN_%s_%d_%d",
                sceneType.name(),
                action.getCouponType().getCode(),
                action.getDenomination().intValue());
    }

    private String generateCouponCode() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16).toUpperCase();
    }

    public CouponDistribution getDistribution(String distributionId) {
        return pendingDistributions.get(distributionId);
    }

    @Data
    @Builder
    public static class CouponDecisionResult {
        private String distributionId;
        private String userId;
        private String couponId;
        private String couponCode;
        private CouponType couponType;
        private BigDecimal denomination;
        private BigDecimal minOrderAmount;
        private SceneType sceneType;
        private String experimentId;
        private String groupId;
        private boolean isRlEnabled;
        private Integer rlActionIndex;
        private LocalDateTime issueTime;
        private LocalDateTime expireTime;
        private boolean success;
        private String blockReason;
        private Integer riskScore;
        private String couponTheme;
        private String personalizedMessage;
        private Map<String, String> displayConfig;
        private Integer priceSensitivityScore;
    }
}

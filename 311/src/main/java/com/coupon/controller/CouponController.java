package com.coupon.controller;

import com.coupon.common.ApiResponse;
import com.coupon.dto.CouponIssueRequest;
import com.coupon.dto.CouponUseRequest;
import com.coupon.model.UserProfile;
import com.coupon.notification.service.CouponNotificationService;
import com.coupon.personalization.service.CouponPersonalizationService;
import com.coupon.redis.service.CouponStockService;
import com.coupon.redis.service.UserProfileCacheService;
import com.coupon.security.service.CouponAntiFraudService;
import com.coupon.service.CouponDistributionService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1/coupon")
public class CouponController {

    private final CouponDistributionService distributionService;
    private final UserProfileCacheService userProfileCacheService;
    private final CouponAntiFraudService antiFraudService;
    private final CouponPersonalizationService personalizationService;
    private final CouponNotificationService notificationService;
    private final CouponStockService couponStockService;

    public CouponController(CouponDistributionService distributionService,
                            UserProfileCacheService userProfileCacheService,
                            CouponAntiFraudService antiFraudService,
                            CouponPersonalizationService personalizationService,
                            CouponNotificationService notificationService,
                            CouponStockService couponStockService) {
        this.distributionService = distributionService;
        this.userProfileCacheService = userProfileCacheService;
        this.antiFraudService = antiFraudService;
        this.personalizationService = personalizationService;
        this.notificationService = notificationService;
        this.couponStockService = couponStockService;
    }

    @PostMapping("/issue")
    public ApiResponse<CouponDistributionService.CouponDecisionResult> issueCoupon(
            @Valid @RequestBody CouponIssueRequest request,
            @RequestHeader(value = "X-Real-IP", required = false) String clientIp,
            @RequestHeader(value = "X-Device-ID", required = false) String deviceId,
            HttpServletRequest servletRequest) {

        String ip = clientIp != null ? clientIp : servletRequest.getRemoteAddr();

        log.info("Receive coupon issue request: userId={}, scene={}, ip={}, device={}",
                request.getUserId(), request.getSceneType(), ip, deviceId);

        CouponDistributionService.CouponDecisionResult result =
                distributionService.decideAndIssueCoupon(request.getUserId(), request.getSceneType(),
                        ip, deviceId);

        if (result == null) {
            return ApiResponse.error("优惠券发放失败，预算不足或限制");
        }

        if (!result.isSuccess()) {
            return ApiResponse.error(403, result.getBlockReason(), result);
        }

        return ApiResponse.success(result);
    }

    @PostMapping("/use")
    public ApiResponse<Map<String, Object>> useCoupon(@Valid @RequestBody CouponUseRequest request) {
        log.info("Receive coupon use request: distributionId={}, orderId={}, amount={}",
                request.getDistributionId(), request.getOrderId(), request.getOrderAmount());

        boolean success = distributionService.useCoupon(
                request.getDistributionId(),
                request.getOrderId(),
                request.getOrderAmount()
        );

        if (success) {
            return ApiResponse.success(Map.of(
                    "success", true,
                    "distributionId", request.getDistributionId()
            ));
        } else {
            return ApiResponse.error("优惠券核销失败");
        }
    }

    @GetMapping("/{distributionId}")
    public ApiResponse<com.coupon.model.CouponDistribution> getCoupon(@PathVariable String distributionId) {
        com.coupon.model.CouponDistribution distribution = distributionService.getDistribution(distributionId);
        if (distribution == null) {
            return ApiResponse.notFound("优惠券记录不存在");
        }
        return ApiResponse.success(distribution);
    }

    @PostMapping("/profile")
    public ApiResponse<UserProfile> saveUserProfile(@RequestBody UserProfile profile) {
        log.info("Save user profile: userId={}", profile.getUserId());
        userProfileCacheService.saveUserProfile(profile);
        return ApiResponse.success(profile);
    }

    @GetMapping("/profile/{userId}")
    public ApiResponse<UserProfile> getUserProfile(@PathVariable String userId) {
        UserProfile profile = userProfileCacheService.getOrCreateDefault(userId);
        return ApiResponse.success(profile);
    }

    @GetMapping("/antifraud/risk/{userId}")
    public ApiResponse<CouponAntiFraudService.FraudCheckResult> getRiskScore(@PathVariable String userId) {
        CouponAntiFraudService.FraudCheckResult result = antiFraudService.getLatestRiskScore(userId);
        if (result == null) {
            return ApiResponse.notFound("未找到用户风险记录");
        }
        return ApiResponse.success(result);
    }

    @GetMapping("/antifraud/stats")
    public ApiResponse<CouponAntiFraudService.FraudStatistics> getFraudStats() {
        return ApiResponse.success(antiFraudService.getFraudStatistics());
    }

    @GetMapping("/personalization/{userId}")
    public ApiResponse<CouponPersonalizationService.PersonalizedCouponRecommendation> getPersonalization(
            @PathVariable String userId) {
        CouponPersonalizationService.PersonalizedCouponRecommendation rec =
                personalizationService.getLatestRecommendation(userId);
        if (rec == null) {
            return ApiResponse.notFound("未找到用户个性化推荐记录");
        }
        return ApiResponse.success(rec);
    }

    @GetMapping("/personalization/sensitivity/{userId}")
    public ApiResponse<CouponPersonalizationService.PriceSensitivity> getPriceSensitivity(
            @PathVariable String userId) {
        UserProfile profile = userProfileCacheService.getOrCreateDefault(userId);
        return ApiResponse.success(personalizationService.calculatePriceSensitivity(userId, profile));
    }

    @GetMapping("/notification/inapp/{userId}")
    public ApiResponse<List<CouponNotificationService.NotificationContent>> getInAppMessages(
            @PathVariable String userId,
            @RequestParam(defaultValue = "20") int limit) {
        return ApiResponse.success(notificationService.getInAppMessages(userId, limit));
    }

    @GetMapping("/notification/stats")
    public ApiResponse<CouponNotificationService.NotificationStatistics> getNotificationStats() {
        return ApiResponse.success(notificationService.getNotificationStatistics());
    }

    @PostMapping("/notification/remind/{distributionId}")
    public ApiResponse<Map<String, Object>> sendExpiryReminder(@PathVariable String distributionId) {
        boolean sent = notificationService.sendCustomExpiryReminder(distributionId);
        return ApiResponse.success(Map.of(
                "success", sent,
                "distributionId", distributionId
        ));
    }

    @PutMapping("/notification/channels/{userId}")
    public ApiResponse<Map<String, Object>> setNotificationChannels(
            @PathVariable String userId,
            @RequestBody List<String> channels) {
        try {
            List<CouponNotificationService.NotificationChannel> channelList = channels.stream()
                    .map(c -> CouponNotificationService.NotificationChannel.valueOf(c.toUpperCase()))
                    .toList();
            notificationService.setUserPreferredChannels(userId, channelList);
            return ApiResponse.success(Map.of(
                    "success", true,
                    "channels", channels
            ));
        } catch (Exception e) {
            return ApiResponse.error("无效的通知渠道: " + e.getMessage());
        }
    }

    @GetMapping("/budget/status")
    public ApiResponse<CouponStockService.BudgetStatus> getBudgetStatus() {
        return ApiResponse.success(couponStockService.getBudgetStatus());
    }

    @PostMapping("/budget/promotion")
    public ApiResponse<CouponStockService.BudgetPromotionConfig> setPromotionConfig(
            @RequestBody CouponStockService.BudgetPromotionConfig config) {
        couponStockService.setPromotionConfig(config);
        return ApiResponse.success(config);
    }
}

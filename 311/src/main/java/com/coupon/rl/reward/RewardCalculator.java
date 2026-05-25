package com.coupon.rl.reward;

import com.coupon.model.CouponDistribution;
import com.coupon.model.UserProfile;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;

@Slf4j
@Component
public class RewardCalculator {

    private static final double REWARD_USAGE_WEIGHT = 0.6;
    private static final double REWARD_ROI_WEIGHT = 0.3;
    private static final double REWARD_COST_WEIGHT = 0.1;

    private static final double COST_PENALTY_SCALE = 0.01;

    public double calculateReward(CouponDistribution distribution, UserProfile profile) {
        if (distribution.getStatus() == null) {
            return 0;
        }

        return switch (distribution.getStatus()) {
            case USED -> calculateUsageReward(distribution, profile);
            case EXPIRED -> -1.0;
            case REVOKED -> -0.5;
            default -> 0;
        };
    }

    private double calculateUsageReward(CouponDistribution distribution, UserProfile profile) {
        double usageReward = calculateUsageComponent(distribution);
        double roiReward = calculateRoiComponent(distribution);
        double costReward = calculateCostComponent(distribution);

        double totalReward = REWARD_USAGE_WEIGHT * usageReward
                + REWARD_ROI_WEIGHT * roiReward
                + REWARD_COST_WEIGHT * costReward;

        log.debug("Reward calculated: usage={}, roi={}, cost={}, total={}",
                usageReward, roiReward, costReward, totalReward);

        return totalReward;
    }

    private double calculateUsageComponent(CouponDistribution distribution) {
        return 1.0;
    }

    private double calculateRoiComponent(CouponDistribution distribution) {
        BigDecimal orderAmount = distribution.getOrderAmount();
        BigDecimal discountAmount = distribution.getDiscountAmount();

        if (orderAmount == null || discountAmount == null
                || discountAmount.compareTo(BigDecimal.ZERO) <= 0) {
            return 0;
        }

        BigDecimal profit = orderAmount.subtract(discountAmount);
        BigDecimal roi = profit.divide(discountAmount, 4, RoundingMode.HALF_UP);

        double normalizedRoi = Math.tanh(roi.doubleValue() / 5.0);

        return Math.max(-1, Math.min(2, normalizedRoi * 2));
    }

    private double calculateCostComponent(CouponDistribution distribution) {
        BigDecimal denomination = distribution.getDenomination();
        if (denomination == null) {
            return 0;
        }

        return -denomination.doubleValue() * COST_PENALTY_SCALE;
    }

    public double calculateImmediateReward(CouponDistribution distribution) {
        BigDecimal denomination = distribution.getDenomination();
        if (denomination == null) {
            return 0;
        }

        return -denomination.doubleValue() * COST_PENALTY_SCALE * 0.1;
    }

    public double calculateDelayedReward(CouponDistribution distribution, UserProfile profile) {
        return calculateReward(distribution, profile);
    }
}

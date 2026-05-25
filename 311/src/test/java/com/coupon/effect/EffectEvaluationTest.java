package com.coupon.effect;

import com.coupon.clickhouse.service.EffectEvaluationService;
import com.coupon.model.enums.CouponType;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;

class EffectEvaluationTest {

    @Test
    void testCouponEffectStatsCalculations() {
        EffectEvaluationService.CouponEffectStats stats = createTestStats(1000, 600, 200);

        assertEquals(60.0, stats.getUsageRate(), 0.01, "Usage rate should be 60%");
        assertEquals(20.0, stats.getExpireRate(), 0.01, "Expire rate should be 20%");
        assertEquals(9.0, stats.getRoi(), 0.01, "ROI should be 9.0");
        assertEquals(new BigDecimal("166.67"), stats.getAvgOrderValue(), "Avg order value should be 166.67");
    }

    @Test
    void testEdgeCasesForStats() {
        EffectEvaluationService.CouponEffectStats zeroStats = createTestStats(0, 0, 0);

        assertEquals(0.0, zeroStats.getUsageRate(), 0.01, "Usage rate should be 0% when no issues");
        assertEquals(0.0, zeroStats.getExpireRate(), 0.01, "Expire rate should be 0% when no issues");
        assertEquals(0.0, zeroStats.getRoi(), 0.01, "ROI should be 0 when no issues");
        assertEquals(BigDecimal.ZERO, zeroStats.getAvgOrderValue(), "Avg order value should be 0 when no usage");

        EffectEvaluationService.CouponEffectStats noDiscountStats = createTestStats(100, 50, 20);
        noDiscountStats.setTotalDiscount(BigDecimal.ZERO);
        assertEquals(0.0, noDiscountStats.getRoi(), 0.01, "ROI should be 0 when no discount");
    }

    @Test
    void testExperimentComparison() {
        EffectEvaluationService.ExperimentComparison comparison =
                new EffectEvaluationService.ExperimentComparison();

        EffectEvaluationService.ExperimentGroupStats control =
                createTestGroupStats("control", 1000, 500);
        control.setUsageRate(50.0);
        control.setRoi(5.0);

        EffectEvaluationService.ExperimentGroupStats experimental =
                createTestGroupStats("rl_group", 1000, 650);
        experimental.setUsageRate(65.0);
        experimental.setRoi(8.0);

        comparison.setControlGroup(control);
        comparison.setExperimentalGroup(experimental);

        comparison.setUsageRateLift(experimental.getUsageRate() - control.getUsageRate());
        comparison.setRoiLift(experimental.getRoi() - control.getRoi());
        comparison.setUsageRateLiftPercent(
                (experimental.getUsageRate() - control.getUsageRate()) / control.getUsageRate() * 100);
        comparison.setRoiLiftPercent(
                (experimental.getRoi() - control.getRoi()) / control.getRoi() * 100);

        assertEquals(15.0, comparison.getUsageRateLift(), 0.01, "Usage rate lift should be 15%");
        assertEquals(3.0, comparison.getRoiLift(), 0.01, "ROI lift should be 3.0");
        assertEquals(30.0, comparison.getUsageRateLiftPercent(), 0.01, "Usage rate lift % should be 30%");
        assertEquals(60.0, comparison.getRoiLiftPercent(), 0.01, "ROI lift % should be 60%");
    }

    @Test
    void testCouponDiscountCalculation() {
        com.coupon.model.Coupon fullDiscountCoupon = com.coupon.model.Coupon.builder()
                .couponType(CouponType.FULL_DISCOUNT)
                .denomination(new BigDecimal("10"))
                .minOrderAmount(new BigDecimal("30"))
                .build();

        assertEquals(new BigDecimal("10"),
                fullDiscountCoupon.calculateDiscount(new BigDecimal("50")));
        assertEquals(BigDecimal.ZERO,
                fullDiscountCoupon.calculateDiscount(new BigDecimal("20")));

        com.coupon.model.Coupon percentageCoupon = com.coupon.model.Coupon.builder()
                .couponType(CouponType.PERCENTAGE_DISCOUNT)
                .discountRate(new BigDecimal("0.9"))
                .maxDiscountAmount(new BigDecimal("20"))
                .minOrderAmount(new BigDecimal("30"))
                .build();

        BigDecimal discount = percentageCoupon.calculateDiscount(new BigDecimal("100"));
        assertEquals(new BigDecimal("10"), discount);

        discount = percentageCoupon.calculateDiscount(new BigDecimal("1000"));
        assertEquals(new BigDecimal("20"), discount, "Should cap at max discount amount");
    }

    @Test
    void testCouponValidity() {
        com.coupon.model.Coupon coupon = com.coupon.model.Coupon.builder()
                .minOrderAmount(new BigDecimal("50"))
                .build();

        assertTrue(coupon.isValid(new BigDecimal("100")));
        assertTrue(coupon.isValid(new BigDecimal("50")));
        assertFalse(coupon.isValid(new BigDecimal("49.99")));
    }

    private EffectEvaluationService.CouponEffectStats createTestStats(
            int issueCount, int usedCount, int expiredCount) {
        EffectEvaluationService.CouponEffectStats stats =
                new EffectEvaluationService.CouponEffectStats();
        stats.setIssueCount(issueCount);
        stats.setUsedCount(usedCount);
        stats.setExpiredCount(expiredCount);
        stats.setTotalDenomination(new BigDecimal("10000"));
        stats.setTotalDiscount(new BigDecimal("6000"));
        stats.setTotalOrderAmount(new BigDecimal("60000"));
        stats.setUniqueUsers(800);
        return stats;
    }

    private EffectEvaluationService.ExperimentGroupStats createTestGroupStats(
            String groupId, int issueCount, int usedCount) {
        EffectEvaluationService.ExperimentGroupStats stats =
                new EffectEvaluationService.ExperimentGroupStats();
        stats.setGroupId(groupId);
        stats.setIssueCount(issueCount);
        stats.setUsedCount(usedCount);
        stats.setExpiredCount(issueCount - usedCount);
        stats.setTotalDenomination(new BigDecimal(issueCount * 10));
        stats.setTotalDiscount(new BigDecimal(usedCount * 10));
        stats.setTotalOrderAmount(new BigDecimal(usedCount * 100));
        stats.setUniqueUsers(issueCount);
        return stats;
    }
}

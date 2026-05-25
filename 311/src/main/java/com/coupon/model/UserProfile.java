package com.coupon.model;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserProfile implements Serializable {

    private static final long serialVersionUID = 1L;

    @JSONField(name = "user_id")
    private String userId;

    @JSONField(name = "consumption_frequency")
    private double consumptionFrequency;

    @JSONField(name = "avg_order_value")
    private double avgOrderValue;

    @JSONField(name = "activity_score")
    private double activityScore;

    @JSONField(name = "total_spend")
    private double totalSpend;

    @JSONField(name = "order_count_30d")
    private int orderCount30d;

    @JSONField(name = "days_since_last_order")
    private int daysSinceLastOrder;

    @JSONField(name = "coupon_usage_rate")
    private double couponUsageRate;

    @JSONField(name = "avg_discount_sensitivity")
    private double avgDiscountSensitivity;

    @JSONField(name = "is_new_user")
    private boolean isNewUser;

    @JSONField(name = "user_level")
    private int userLevel;

    @JSONField(name = "register_time")
    private LocalDateTime registerTime;

    @JSONField(name = "last_active_time")
    private LocalDateTime lastActiveTime;

    @JSONField(name = "update_time")
    private LocalDateTime updateTime;

    @JSONField(name = "coupon_issue_count_7d")
    private int couponIssueCount7d;

    @JSONField(name = "coupon_use_count_7d")
    private int couponUseCount7d;

    @JSONField(name = "coupon_type_distribution_7d")
    private double[] couponTypeDistribution7d;

    @JSONField(name = "coupon_denomination_distribution_7d")
    private double[] couponDenominationDistribution7d;

    @JSONField(name = "days_since_last_coupon")
    private int daysSinceLastCoupon;

    @JSONField(name = "last_coupon_type")
    private Integer lastCouponType;

    @JSONField(name = "last_coupon_denomination")
    private Integer lastCouponDenomination;

    @JSONField(name = "birthday")
    private String birthday;

    @JSONField(name = "preferred_categories")
    private List<String> preferredCategories;

    private static final int STATE_DIM = 18;
    private static final int COUPON_TYPE_COUNT = 5;
    private static final int DENOMINATION_BUCKETS = 4;

    public double[] toStateVector() {
        double[] state = new double[STATE_DIM];
        int idx = 0;

        state[idx++] = normalize(consumptionFrequency, 0, 30);
        state[idx++] = normalize(avgOrderValue, 0, 1000);
        state[idx++] = normalize(activityScore, 0, 100);
        state[idx++] = normalize(orderCount30d, 0, 50);
        state[idx++] = normalize(daysSinceLastOrder, 0, 180);
        state[idx++] = normalize(couponUsageRate, 0, 1);
        state[idx++] = normalize(avgDiscountSensitivity, 0, 1);
        state[idx++] = isNewUser ? 1.0 : 0.0;

        state[idx++] = normalize(couponIssueCount7d, 0, 10);
        state[idx++] = normalize(couponUseCount7d, 0, 10);
        state[idx++] = normalize(daysSinceLastCoupon, 0, 30);

        double[] typeDist = getSafeCouponTypeDistribution();
        for (int i = 0; i < COUPON_TYPE_COUNT; i++) {
            state[idx++] = typeDist[i];
        }

        double denominationFreq = lastCouponDenomination != null ? 1.0 : 0.0;
        state[idx++] = denominationFreq;
        state[idx++] = lastCouponType != null ? normalize(lastCouponType, 1, 5) : 0.0;

        return state;
    }

    private double[] getSafeCouponTypeDistribution() {
        double[] safeDist = new double[COUPON_TYPE_COUNT];
        if (couponTypeDistribution7d != null && couponTypeDistribution7d.length > 0) {
            int len = Math.min(COUPON_TYPE_COUNT, couponTypeDistribution7d.length);
            System.arraycopy(couponTypeDistribution7d, 0, safeDist, 0, len);
        }
        double sum = 0;
        for (double v : safeDist) sum += v;
        if (sum > 0) {
            for (int i = 0; i < safeDist.length; i++) {
                safeDist[i] /= sum;
            }
        }
        return safeDist;
    }

    public static int getStateDimension() {
        return STATE_DIM;
    }

    public void initCouponHistoryArrays() {
        this.couponTypeDistribution7d = new double[COUPON_TYPE_COUNT];
        this.couponDenominationDistribution7d = new double[DENOMINATION_BUCKETS];
    }

    public void recordCouponIssue(int couponType, int denomination) {
        if (couponTypeDistribution7d == null) {
            initCouponHistoryArrays();
        }

        int typeIdx = Math.max(0, Math.min(COUPON_TYPE_COUNT - 1, couponType - 1));
        couponTypeDistribution7d[typeIdx]++;
        couponIssueCount7d++;
        daysSinceLastCoupon = 0;
        lastCouponType = couponType;
        lastCouponDenomination = denomination;

        int denomIdx = Math.min(DENOMINATION_BUCKETS - 1, denomination / 15);
        couponDenominationDistribution7d[denomIdx]++;
    }

    public boolean hasRecentSimilarCoupon(int couponType, int denomination) {
        if (lastCouponType == null || lastCouponDenomination == null) {
            return false;
        }
        if (daysSinceLastCoupon >= 3) {
            return false;
        }
        boolean sameType = lastCouponType == couponType;
        boolean similarDenomination = Math.abs(lastCouponDenomination - denomination) <= 5;
        return sameType && similarDenomination;
    }

    public double getCouponTypeFrequency(int couponType) {
        double[] dist = getSafeCouponTypeDistribution();
        int idx = Math.max(0, Math.min(COUPON_TYPE_COUNT - 1, couponType - 1));
        return dist[idx];
    }

    private double normalize(double value, double min, double max) {
        return Math.max(0, Math.min(1, (value - min) / (max - min)));
    }
}

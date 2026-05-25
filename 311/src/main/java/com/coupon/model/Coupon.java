package com.coupon.model;

import com.alibaba.fastjson2.annotation.JSONField;
import com.coupon.model.enums.CouponType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Coupon implements Serializable {

    private static final long serialVersionUID = 1L;

    @JSONField(name = "coupon_id")
    private String couponId;

    @JSONField(name = "coupon_type")
    private CouponType couponType;

    @JSONField(name = "denomination")
    private BigDecimal denomination;

    @JSONField(name = "discount_rate")
    private BigDecimal discountRate;

    @JSONField(name = "min_order_amount")
    private BigDecimal minOrderAmount;

    @JSONField(name = "max_discount_amount")
    private BigDecimal maxDiscountAmount;

    @JSONField(name = "valid_days")
    private int validDays;

    @JSONField(name = "stock")
    private int stock;

    @JSONField(name = "used_count")
    private int usedCount;

    @JSONField(name = "expire_time")
    private LocalDateTime expireTime;

    @JSONField(name = "create_time")
    private LocalDateTime createTime;

    @JSONField(name = "scene_code")
    private Integer sceneCode;

    @JSONField(name = "category_code")
    private String categoryCode;

    @JSONField(name = "description")
    private String description;

    public BigDecimal calculateDiscount(BigDecimal orderAmount) {
        if (orderAmount.compareTo(minOrderAmount) < 0) {
            return BigDecimal.ZERO;
        }

        return switch (couponType) {
            case FULL_DISCOUNT -> denomination;
            case PERCENTAGE_DISCOUNT -> {
                BigDecimal discount = orderAmount.multiply(BigDecimal.ONE.subtract(discountRate));
                yield discount.compareTo(maxDiscountAmount) > 0 ? maxDiscountAmount : discount;
            }
            case FREE_SHIPPING, NEW_USER_ONLY -> denomination;
            case CATEGORY_SPECIFIC -> denomination;
        };
    }

    public boolean isValid(BigDecimal orderAmount) {
        return orderAmount.compareTo(minOrderAmount) >= 0;
    }
}

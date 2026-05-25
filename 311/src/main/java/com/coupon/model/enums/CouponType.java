package com.coupon.model.enums;

import lombok.Getter;

@Getter
public enum CouponType {
    FULL_DISCOUNT(1, "满减券", false),
    PERCENTAGE_DISCOUNT(2, "折扣券", false),
    FREE_SHIPPING(3, "免邮券", true),
    NEW_USER_ONLY(4, "新人专享券", false),
    CATEGORY_SPECIFIC(5, "品类券", true);

    private final int code;
    private final String desc;
    private final boolean specialHandling;

    CouponType(int code, String desc, boolean specialHandling) {
        this.code = code;
        this.desc = desc;
        this.specialHandling = specialHandling;
    }

    public static CouponType fromCode(int code) {
        for (CouponType type : values()) {
            if (type.code == code) {
                return type;
            }
        }
        return FULL_DISCOUNT;
    }
}

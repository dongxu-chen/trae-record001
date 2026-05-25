package com.coupon.model.enums;

import lombok.Getter;

@Getter
public enum CouponStatus {
    ISSUED(0, "已发放"),
    USED(1, "已使用"),
    EXPIRED(2, "已过期"),
    REVOKED(3, "已撤回");

    private final int code;
    private final String desc;

    CouponStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static CouponStatus fromCode(int code) {
        for (CouponStatus status : values()) {
            if (status.code == code) {
                return status;
            }
        }
        return ISSUED;
    }
}

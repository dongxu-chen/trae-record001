package com.coupon.model.enums;

import lombok.Getter;

@Getter
public enum SceneType {
    NEW_USER(1, "新人场景", 0.3),
    REPURCHASE(2, "复购场景", 0.4),
    WAKE_UP(3, "唤醒场景", 0.3);

    private final int code;
    private final String desc;
    private final double defaultTrafficWeight;

    SceneType(int code, String desc, double defaultTrafficWeight) {
        this.code = code;
        this.desc = desc;
        this.defaultTrafficWeight = defaultTrafficWeight;
    }

    public static SceneType fromCode(int code) {
        for (SceneType type : values()) {
            if (type.code == code) {
                return type;
            }
        }
        return REPURCHASE;
    }
}

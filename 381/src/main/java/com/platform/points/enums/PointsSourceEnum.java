package com.platform.points.enums;

import lombok.Getter;

@Getter
public enum PointsSourceEnum {

    SIGN_IN(1, "签到"),
    CONSUME(2, "消费"),
    ACTIVITY(3, "活动"),
    EXCHANGE(4, "兑换"),
    EXPIRE(5, "过期");

    private final Integer code;
    private final String desc;

    PointsSourceEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static PointsSourceEnum getByCode(Integer code) {
        for (PointsSourceEnum e : values()) {
            if (e.code.equals(code)) {
                return e;
            }
        }
        return null;
    }
}

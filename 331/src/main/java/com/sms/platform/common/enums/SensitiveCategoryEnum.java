package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum SensitiveCategoryEnum {
    PORNOGRAPHY(1, "涉黄"),
    POLITICS(2, "涉政"),
    GAMBLING(3, "涉赌"),
    FRAUD(4, "诈骗"),
    OTHER(5, "其他");

    private final Integer code;
    private final String desc;

    public static SensitiveCategoryEnum getByCode(Integer code) {
        for (SensitiveCategoryEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

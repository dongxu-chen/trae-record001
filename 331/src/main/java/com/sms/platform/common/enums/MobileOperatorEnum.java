package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum MobileOperatorEnum {
    CHINA_MOBILE(1, "中国移动"),
    CHINA_UNICOM(2, "中国联通"),
    CHINA_TELECOM(3, "中国电信"),
    OTHER(4, "其他");

    private final Integer code;
    private final String name;

    public static MobileOperatorEnum getByCode(Integer code) {
        for (MobileOperatorEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

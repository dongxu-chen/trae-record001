package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum SmsTypeEnum {
    VERIFICATION(1, "验证码"),
    NOTIFICATION(2, "通知"),
    MARKETING(3, "营销");

    private final Integer code;
    private final String desc;

    public static SmsTypeEnum getByCode(Integer code) {
        for (SmsTypeEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

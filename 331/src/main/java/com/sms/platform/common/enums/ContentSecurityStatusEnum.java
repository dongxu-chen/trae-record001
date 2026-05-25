package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ContentSecurityStatusEnum {
    NOT_CHECKED(0, "未检测"),
    PASSED(1, "检测通过"),
    REJECTED(2, "检测不通过");

    private final Integer code;
    private final String desc;

    public static ContentSecurityStatusEnum getByCode(Integer code) {
        for (ContentSecurityStatusEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

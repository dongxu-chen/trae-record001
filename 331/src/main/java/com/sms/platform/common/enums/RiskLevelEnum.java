package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum RiskLevelEnum {
    NONE(0, "无风险"),
    LOW(1, "低风险"),
    MEDIUM(2, "中风险"),
    HIGH(3, "高风险");

    private final Integer code;
    private final String desc;

    public static RiskLevelEnum getByCode(Integer code) {
        for (RiskLevelEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

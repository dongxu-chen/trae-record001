package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum SendStatusEnum {
    PENDING(0, "待发送"),
    SUCCESS(1, "发送成功"),
    FAILED(2, "发送失败"),
    BLACKLIST(3, "黑名单拦截"),
    RATE_LIMIT(4, "限流拦截"),
    RECEIPT_TIMEOUT(5, "回执超时"),
    CONTENT_VIOLATION(6, "内容违规"),
    TIME_POLICY_LIMIT(7, "时段限制");

    private final Integer code;
    private final String desc;

    public static SendStatusEnum getByCode(Integer code) {
        for (SendStatusEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

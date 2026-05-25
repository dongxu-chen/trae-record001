package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ReceiptStatusEnum {
    PENDING(0, "待回执"),
    SUCCESS(1, "回执成功"),
    FAILED(2, "回执失败"),
    TIMEOUT(3, "回执超时");

    private final Integer code;
    private final String desc;

    public static ReceiptStatusEnum getByCode(Integer code) {
        for (ReceiptStatusEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }
}

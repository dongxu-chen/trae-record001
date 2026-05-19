package com.pushplatform.common.enums;

import lombok.Getter;

@Getter
public enum PushStatusEnum {

    PENDING(0, "待推送"),
    SUCCESS(1, "推送成功"),
    FAILED(2, "推送失败"),
    CALLBACK_SUCCESS(3, "回调成功"),
    CALLBACK_FAILED(4, "回调失败");

    private final Integer code;
    private final String desc;

    PushStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}

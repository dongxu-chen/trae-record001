package com.pushcenter.enums;

import lombok.Getter;

@Getter
public enum MessageStatus {

    PENDING("pending", "待发送"),
    SENDING("sending", "发送中"),
    SUCCESS("success", "发送成功"),
    FAILED("failed", "发送失败"),
    RETRYING("retrying", "重试中");

    private final String code;
    private final String name;

    MessageStatus(String code, String name) {
        this.code = code;
        this.name = name;
    }
}

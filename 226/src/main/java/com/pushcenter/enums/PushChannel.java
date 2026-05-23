package com.pushcenter.enums;

import lombok.Getter;

@Getter
public enum PushChannel {

    EMAIL("email", "邮件", 1),
    SMS("sms", "短信", 2),
    DINGTALK("dingtalk", "钉钉", 3),
    WECHAT_WORK("wechat_work", "企业微信", 4),
    APP_PUSH("app_push", "App推送", 5);

    private final String code;
    private final String name;
    private final int priority;

    PushChannel(String code, String name, int priority) {
        this.code = code;
        this.name = name;
        this.priority = priority;
    }

    public static PushChannel fromCode(String code) {
        for (PushChannel channel : values()) {
            if (channel.getCode().equals(code)) {
                return channel;
            }
        }
        return null;
    }
}

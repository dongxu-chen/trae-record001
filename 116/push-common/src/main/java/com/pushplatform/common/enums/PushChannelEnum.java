package com.pushplatform.common.enums;

import lombok.Getter;

@Getter
public enum PushChannelEnum {

    APNS("apns", "苹果推送"),
    FCM("fcm", "谷歌推送"),
    WEBSOCKET("websocket", "WebSocket推送");

    private final String code;
    private final String desc;

    PushChannelEnum(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static PushChannelEnum getByCode(String code) {
        for (PushChannelEnum channel : values()) {
            if (channel.code.equals(code)) {
                return channel;
            }
        }
        return null;
    }
}

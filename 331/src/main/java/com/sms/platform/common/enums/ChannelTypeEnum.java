package com.sms.platform.common.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ChannelTypeEnum {
    ALIYUN(1, "阿里云", "aliyun"),
    TENCENT(2, "腾讯云", "tencent");

    private final Integer code;
    private final String name;
    private final String provider;

    public static ChannelTypeEnum getByCode(Integer code) {
        for (ChannelTypeEnum e : values()) {
            if (e.getCode().equals(code)) {
                return e;
            }
        }
        return null;
    }

    public static ChannelTypeEnum getByProvider(String provider) {
        for (ChannelTypeEnum e : values()) {
            if (e.getProvider().equals(provider)) {
                return e;
            }
        }
        return null;
    }
}

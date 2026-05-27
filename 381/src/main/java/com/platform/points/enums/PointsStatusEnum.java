package com.platform.points.enums;

import lombok.Getter;

@Getter
public enum PointsStatusEnum {

    NORMAL(0, "正常"),
    EXPIRED(1, "已过期"),
    USED(2, "已使用");

    private final Integer code;
    private final String desc;

    PointsStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}

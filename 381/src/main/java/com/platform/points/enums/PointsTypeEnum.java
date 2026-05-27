package com.platform.points.enums;

import lombok.Getter;

@Getter
public enum PointsTypeEnum {

    GRANT(1, "发放"),
    DEDUCT(2, "扣减");

    private final Integer code;
    private final String desc;

    PointsTypeEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
